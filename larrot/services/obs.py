"""OBS: S3-compatible object storage, v2-signed, on its own port."""

import hashlib
import re
import time
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
from ..core.jobs import new_id, now_millis
from ..middleware import obs_middleware
from xml.sax.saxutils import escape

router = APIRouter()


def _xml_escape(s):
    return escape(s or "")


def _error_xml(code, message, extra=None):
    rid = new_id().upper()
    body = f'<?xml version="1.0" encoding="UTF-8"?>\n<Error><Code>{code}</Code>'
    body += f'<Message>{_xml_escape(message)}</Message>'
    body += f'<RequestId>{rid}</RequestId><HostId>{rid}</HostId>'
    for k, v in (extra or {}).items():
        body += f'<{k}>{_xml_escape(v)}</{k}>'
    body += '</Error>'
    return PlainTextResponse(body, status_code=200, media_type="application/xml")


def _error(code, message, status=404, extra=None):
    resp = _error_xml(code, message, extra)
    resp.status_code = status
    return resp


def _resolve_bucket(request):
    """Resolve bucket from Host (virtual-host) or path (path-style)."""
    host = request.headers.get("host", "127.0.0.1:8201").split(":")[0]
    path = request.url.path

    if "." in host and host != "localhost" and not host.replace(".", "").isdigit():
        first = host.split(".")[0]
        if first and first != "obs":
            return first, path  # virtual-host

    trimmed = path.lstrip("/")
    if "/" in trimmed:
        bucket, _, key = trimmed.partition("/")
        return bucket, f"/{key}"
    elif trimmed:
        return trimmed, "/"
    return None, "/"


# ---------------------------------------------------------------------------
# bucket + object handlers (catch-all)
# ---------------------------------------------------------------------------

@router.api_route("/{path:path}", methods=["GET", "PUT", "POST", "DELETE", "HEAD"])
async def obs_handler(request: Request, path: str):
    state = request.app.state.sim
    bucket, key_path = _resolve_bucket(request)
    method = request.method
    query = dict(request.query_params)

    if not bucket:
        return _list_buckets(state)

    if bucket not in state.obs_buckets and method != "PUT":
        return _error("NoSuchBucket", "The specified bucket does not exist",
                      extra={"BucketName": bucket})

    if key_path == "/" or not key_path.lstrip("/"):
        return await _bucket_handler(state, request, bucket, method, query)
    return await _object_handler(state, request, bucket, key_path.lstrip("/"), method, query)


def _list_buckets(state):
    owner = state.account["domain_id"]
    body = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    body += '<ListAllMyBucketsResult xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">\n'
    body += f'<Owner><ID>{owner}</ID></Owner>\n<Buckets>\n'
    for b in state.obs_buckets.values():
        body += f'<Bucket><Name>{_xml_escape(b["name"])}</Name>'
        body += f'<CreationDate>{b["created_at"]}</CreationDate>'
        body += f'<Location>{_xml_escape(b["location"])}</Location>'
        body += '<BucketType>OBJECT</BucketType></Bucket>\n'
    body += '</Buckets>\n</ListAllMyBucketsResult>'
    return PlainTextResponse(body, media_type="application/xml")


async def _bucket_handler(state, request, bucket, method, query):
    if method == "PUT":
        if "versioning" in query:
            b = state.obs_buckets.get(bucket)
            if not b:
                return _error("NoSuchBucket", "The specified bucket does not exist",
                              extra={"BucketName": bucket}, status=404)
            body_bytes = await request.body()
            b["versioning"] = b"Enabled" in body_bytes
            return PlainTextResponse("", status_code=200)
        if "acl" in query or "tagging" in query:
            b = state.obs_buckets.get(bucket)
            if not b:
                return _error("NoSuchBucket", "The specified bucket does not exist",
                              extra={"BucketName": bucket}, status=404)
            body_bytes = await request.body()
            if "acl" in query:
                b["acl"] = body_bytes.decode(errors="replace")[:512]
            else:
                b["tagging"] = body_bytes.decode(errors="replace")[:512]
            return PlainTextResponse("", status_code=200)
        if bucket in state.obs_buckets:
            return _error("BucketAlreadyOwnedByYou",
                "Your previous request for creating a bucket with this name succeeds and you already own the bucket.",
                status=409, extra={"BucketName": bucket})
        if len(state.obs_buckets) >= 100:
            return _error("TooManyBuckets",
                "You have attempted to create more buckets than allowed.", status=400)
        state.obs_buckets[bucket] = {"name": bucket, "created_at": now_millis(), "location": "sim"}
        resp = PlainTextResponse("", status_code=200)
        resp.headers["Location"] = f"/{bucket}"
        return resp

    if method == "HEAD":
        return PlainTextResponse("", status_code=200 if bucket in state.obs_buckets else 404)

    if method == "POST" and "delete" in query:
        import base64
        raw = await request.body()
        text = raw.decode(errors="replace")
        keys = re.findall(r"<Key>([^<]+)</Key>", text)
        quiet = "<Quiet>true" in text
        deleted, not_found = [], []
        for k in keys:
            sk = f"{bucket}/{k}"
            if state.obs_objects.pop(sk, None) is not None:
                deleted.append(k)
            else:
                not_found.append(k)
        if quiet:
            return PlainTextResponse("", status_code=200)
        body = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        body += '<DeleteResult xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">\n'
        for k in deleted:
            body += f'<Deleted><Key>{_xml_escape(k)}</Key></Deleted>\n'
        for k in not_found:
            body += (f'<Error><Key>{_xml_escape(k)}</Key>'
                     '<Code>NoSuchKey</Code></Error>\n')
        body += '</DeleteResult>'
        return PlainTextResponse(body, media_type="application/xml")

    if method == "DELETE":
        has_objects = any(k.startswith(f"{bucket}/") for k in state.obs_objects)
        if has_objects:
            return _error("BucketNotEmpty", "The bucket you tried to delete is not empty",
                          status=409, extra={"BucketName": bucket})
        del state.obs_buckets[bucket]
        return PlainTextResponse("", status_code=204)

    if method == "GET":
        b = state.obs_buckets.get(bucket)
        if "versioning" in query:
            if not b:
                return _error("NoSuchBucket", "The specified bucket does not exist",
                              extra={"BucketName": bucket}, status=404)
            status = "Enabled" if b.get("versioning") else "Disabled"
            body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    f'<VersioningConfiguration xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">'
                    f'<Status>{status}</Status></VersioningConfiguration>')
            return PlainTextResponse(body, media_type="application/xml")
        if "acl" in query or "tagging" in query:
            if not b:
                return _error("NoSuchBucket", "The specified bucket does not exist",
                              extra={"BucketName": bucket}, status=404)
            key = "acl" if "acl" in query else "tagging"
            if key == "acl":
                body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        '<AccessControlPolicy xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">'
                        '<Owner><ID>' + state.account["domain_id"] + '</ID></Owner>'
                        '<AccessControlList><Grant><Grantee><ID>' + state.account["domain_id"] +
                        '</ID></Grantee><Permission>FULL_CONTROL</Permission></Grant>'
                        '</AccessControlList></AccessControlPolicy>')
            else:
                tags = b.get("tagging", "")
                body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        '<Tagging xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">'
                        '<TagSet>' + (tags if tags else "") + '</TagSet></Tagging>')
            return PlainTextResponse(body, media_type="application/xml")
        if "location" in query:
            body = ('<?xml xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<LocationConstraint xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">sim</LocationConstraint>')
            return PlainTextResponse(body, media_type="application/xml")
        if "uploads" in query:
            uploads = [(uid, u) for uid, u in state.obs_uploads.items()
                       if u["bucket"] == bucket]
            body = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            body += '<ListMultipartUploadsResult xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">\n'
            body += f'<Bucket>{_xml_escape(bucket)}</Bucket>\n'
            for uid, u in uploads:
                body += (f'<Upload><Key>{_xml_escape(u["key"])}</Key>'
                        f'<UploadId>{uid}</UploadId>'
                        f'<Initiated>{u.get("initiated", "")}</Initiated></Upload>\n')
            body += '</ListMultipartUploadsResult>'
            return PlainTextResponse(body, media_type="application/xml")
        if "storageinfo" in query:
            n_objs = sum(1 for k in state.obs_objects if k.startswith(f"{bucket}/"))
            size = sum(len(v["data"]) for k, v in state.obs_objects.items()
                       if k.startswith(f"{bucket}/"))
            body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<GetBucketStorageInfoResult '
                    'xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">'
                    f'<Size>{size}</Size><ObjectNumber>{n_objs}</ObjectNumber>'
                    '</GetBucketStorageInfoResult>')
            return PlainTextResponse(body, media_type="application/xml")
        return _list_objects(state, bucket, query)

    return _error("MethodNotAllowed", "The specified method is not allowed against this resource.", status=405)


def _list_objects(state, bucket, query):
    prefix = query.get("prefix", "")
    marker = query.get("marker", "")
    max_keys = min(int(query.get("max-keys", 1000)), 1000)
    delimiter = query.get("delimiter", "")
    owner = state.account["domain_id"]

    objs = sorted(
        [(k, v) for k, v in state.obs_objects.items()
         if v["bucket"] == bucket and v["key"].startswith(prefix) and v["key"] > marker],
        key=lambda x: x[1]["key"],
    )

    contents = ""
    common_prefixes = set()
    count = 0
    truncated = False
    next_marker = ""

    for _, o in objs:
        if count >= max_keys:
            truncated = True
            break
        if delimiter:
            rest = o["key"][len(prefix):]
            pos = rest.find(delimiter)
            if pos >= 0:
                cp = o["key"][:len(prefix) + pos + len(delimiter)]
                if cp not in common_prefixes:
                    common_prefixes.add(cp)
                    count += 1
                continue
        contents += f'<Contents><Key>{_xml_escape(o["key"])}</Key>'
        contents += f'<LastModified>{o["last_modified"]}</LastModified>'
        contents += f'<ETag>{o["etag"]}</ETag><Size>{len(o["data"])}</Size>'
        contents += f'<Owner><ID>{owner}</ID><DisplayName>sim</DisplayName></Owner>'
        contents += '<StorageClass>STANDARD</StorageClass></Contents>\n'
        next_marker = o["key"]
        count += 1

    body = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    body += '<ListBucketResult xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">\n'
    body += f'<Name>{_xml_escape(bucket)}</Name>\n'
    body += f'<Prefix>{_xml_escape(prefix)}</Prefix>\n'
    body += f'<Marker>{_xml_escape(marker)}</Marker>\n'
    body += f'<MaxKeys>{max_keys}</MaxKeys>\n'
    if delimiter:
        body += f'<Delimiter>{_xml_escape(delimiter)}</Delimiter>\n'
    body += f'<IsTruncated>{str(truncated).lower()}</IsTruncated>\n'
    if truncated:
        body += f'<NextMarker>{_xml_escape(next_marker)}</NextMarker>\n'
    body += contents
    for cp in sorted(common_prefixes):
        body += f'<CommonPrefixes><Prefix>{_xml_escape(cp)}</Prefix></CommonPrefixes>\n'
    body += '</ListBucketResult>'
    return PlainTextResponse(body, media_type="application/xml")


async def _object_handler(state, request, bucket, key, method, query):
    store_key = f"{bucket}/{key}"

    if method == "PUT":
        if "partNumber" in query and "uploadId" in query:
            return await _upload_part(state, request, bucket, key, query)
        copy_source = request.headers.get("x-obs-copy-source", "")
        if copy_source:
            src_key = copy_source.lstrip("/")
            src_obj = state.obs_objects.get(src_key)
            if not src_obj:
                return _error("NoSuchKey", "The source object does not exist",
                              extra={"Key": src_key})
            state.obs_objects[store_key] = {
                "bucket": bucket, "key": key, "data": src_obj["data"],
                "etag": src_obj["etag"], "content_type": src_obj["content_type"],
                "last_modified": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
                "metadata": dict(src_obj["metadata"]),
            }
            body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<CopyObjectResult '
                    'xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">'
                    f'<ETag>{src_obj["etag"]}</ETag>'
                    f'<LastModified>{state.obs_objects[store_key]["last_modified"]}'
                    '</LastModified></CopyObjectResult>')
            return PlainTextResponse(body, media_type="application/xml")
        data = await request.body()
        if len(data) > 5 * 1024 * 1024 * 1024:
            return _error("EntityTooLarge", "Your proposed upload exceeds the maximum size allowed", status=400)

        # Content-MD5 verification
        md5_hdr = request.headers.get("content-md5")
        if md5_hdr:
            import base64
            computed = base64.b64encode(hashlib.md5(data).digest()).decode()
            if computed != md5_hdr:
                return _error("BadDigest", "The Content-MD5 you specified did not match what we received.", status=400)

        etag = f'"{hashlib.md5(data).hexdigest()}"'
        content_type = request.headers.get("content-type", "binary/octet-stream")
        metadata = {k: v for k, v in request.headers.items() if k.startswith("x-obs-meta-")}

        state.obs_objects[store_key] = {
            "bucket": bucket, "key": key, "data": data,
            "etag": etag, "content_type": content_type,
            "last_modified": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            "metadata": metadata,
        }
        resp = PlainTextResponse("", status_code=200)
        resp.headers["ETag"] = etag
        return resp

    if method == "GET":
        if "uploadId" in query:
            return _list_parts(state, bucket, key, query)
        obj = state.obs_objects.get(store_key)
        if not obj:
            return _error("NoSuchKey", "The resource you requested does not exist",
                          extra={"Key": key})
        # Range support
        data = obj["data"]
        range_hdr = request.headers.get("range")
        if range_hdr and range_hdr.startswith("bytes="):
            spec = range_hdr[6:]
            start_s, _, end_s = spec.partition("-")
            ln = len(data)
            if start_s:
                start = int(start_s)
                end = int(end_s) if end_s else ln - 1
            else:
                suffix = int(end_s)
                start, end = max(ln - suffix, 0), ln - 1
            if start >= ln:
                return _error("InvalidRange", "The requested range is not satisfiable", status=416)
            data = data[start:end + 1]

        resp = PlainTextResponse(bytes(data), status_code=200,
                                  media_type=obj["content_type"])
        resp.headers["ETag"] = obj["etag"]
        resp.headers["Last-Modified"] = obj["last_modified"]
        resp.headers["Accept-Ranges"] = "bytes"
        for k, v in obj["metadata"].items():
            resp.headers[k] = v
        return resp

    if method == "HEAD":
        obj = state.obs_objects.get(store_key)
        if not obj:
            return PlainTextResponse("", status_code=404)
        resp = PlainTextResponse("", status_code=200)
        resp.headers["ETag"] = obj["etag"]
        resp.headers["Content-Type"] = obj["content_type"]
        resp.headers["Content-Length"] = str(len(obj["data"]))
        resp.headers["Last-Modified"] = obj["last_modified"]
        return resp

    if method == "DELETE":
        if "uploadId" in query:
            state.obs_uploads.pop(query["uploadId"], None)
            return PlainTextResponse("", status_code=204)
        state.obs_objects.pop(store_key, None)
        return PlainTextResponse("", status_code=204)

    if method == "POST":
        if "uploads" in query:
            return _initiate_upload(state, bucket, key)
        if "uploadId" in query:
            return await _complete_upload(state, request, bucket, key, query)

    return _error("MethodNotAllowed", "The specified method is not allowed against this resource.", status=405)


# ---------------------------------------------------------------------------
# multipart upload
# ---------------------------------------------------------------------------

def _initiate_upload(state, bucket, key):
    upload_id = new_id()
    state.obs_uploads[upload_id] = {"bucket": bucket, "key": key,
                                     "initiated": now_millis(), "parts": {}}
    body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<InitiateMultipartUploadResult xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">'
            f'<Bucket>{_xml_escape(bucket)}</Bucket><Key>{_xml_escape(key)}</Key>'
            f'<UploadId>{upload_id}</UploadId></InitiateMultipartUploadResult>')
    return PlainTextResponse(body, media_type="application/xml")


async def _upload_part(state, request, bucket, key, query):
    upload_id = query["uploadId"]
    part_no = int(query["partNumber"])
    upload = state.obs_uploads.get(upload_id)
    if not upload or upload["bucket"] != bucket or upload["key"] != key:
        return _error("NoSuchUpload", "The specified upload does not exist.")

    data = await request.body()
    etag = f'"{hashlib.md5(data).hexdigest()}"'
    upload["parts"][part_no] = (data, etag)

    resp = PlainTextResponse("", status_code=200)
    resp.headers["ETag"] = etag
    return resp


def _list_parts(state, bucket, key, query):
    upload_id = query["uploadId"]
    upload = state.obs_uploads.get(upload_id)
    if not upload:
        return _error("NoSuchUpload", "The specified upload does not exist.")

    body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<ListPartsResult xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">\n'
            f'<Bucket>{_xml_escape(bucket)}</Bucket><Key>{_xml_escape(key)}</Key>'
            f'<UploadId>{_xml_escape(upload_id)}</UploadId>\n'
            '<PartNumberMarker>0</PartNumberMarker><NextPartNumberMarker>0</NextPartNumberMarker>'
            '<MaxParts>1000</MaxParts><IsTruncated>false</IsTruncated>\n')
    for no, (data, etag) in sorted(upload["parts"].items()):
        body += f'<Part><PartNumber>{no}</PartNumber><ETag>{etag}</ETag><Size>{len(data)}</Size></Part>\n'
    body += '</ListPartsResult>'
    return PlainTextResponse(body, media_type="application/xml")


async def _complete_upload(state, request, bucket, key, query):
    upload_id = query["uploadId"]
    upload = state.obs_uploads.get(upload_id)
    if not upload:
        return _error("NoSuchUpload", "The specified upload does not exist.")

    body = await request.body()
    xml = body.decode("utf-8", errors="replace")
    wanted = [int(m) for m in re.findall(r"<PartNumber>(\d+)</PartNumber>", xml)]

    for n in wanted:
        if n not in upload["parts"]:
            return _error("InvalidPart", "One or more of the specified parts could not be found.", status=400)

    data = b"".join(upload["parts"][n][0] for n in wanted)
    etag = f'"{hashlib.md5(data).hexdigest()}"'

    del state.obs_uploads[upload_id]
    state.obs_objects[f"{bucket}/{key}"] = {
        "bucket": bucket, "key": key, "data": data,
        "etag": etag, "content_type": "binary/octet-stream",
        "last_modified": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
        "metadata": {},
    }

    body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<CompleteMultipartUploadResult xmlns="http://obs.myhuaweicloud.com/doc/2015-06-30/">'
            f'<Location>http://sim/{_xml_escape(bucket)}/{_xml_escape(key)}</Location>'
            f'<Bucket>{_xml_escape(bucket)}</Bucket><Key>{_xml_escape(key)}</Key>'
            f'<ETag>{etag}</ETag></CompleteMultipartUploadResult>')
    return PlainTextResponse(body, media_type="application/xml")
