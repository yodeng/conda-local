from .utils import *

from conda.core.path_actions import *

__all__ = ["Extract", "Download"]


class Download(object):
    def __init__(self, axn, exn, lock):
        self.axn = axn
        self.exn = exn
        axn.verify()
        exn.verify()
        self.lock = lock
        self.target_pkgs_dir = axn.target_pkgs_dir
        os.makedirs(self.target_pkgs_dir, exist_ok=True)
        self.target_package_cache = PackageCacheData(self.target_pkgs_dir)
        self.progress_bar = None

    def download(self):
        prec_or_spec = self.exn.record_or_spec
        axn = self.axn
        outpath = axn.target_full_path
        url = axn.url
        size = axn.size
        offset = 0
        if isfile(outpath):
            offset = os.path.getsize(outpath)
            if offset == size:
                if check_md5(outpath) == axn.md5:
                    LOCAL_CONDA_LOG.info("%s already esists", outpath)
                    return
                else:
                    os.remove(outpath)
                    offset = 0
        headers = {"Range": "bytes={}-".format(offset)}
        desc = ''
        if prec_or_spec.name and prec_or_spec.version:
            desc = "%s-%s" % (prec_or_spec.name or '',
                              prec_or_spec.version or '')
        size_str = size and human_bytes(size) or ''
        if len(desc) > 0:
            desc = "%-20.20s | " % desc
        if len(size_str) > 0:
            desc += "%-9s | " % size_str
        md5 = hashlib.md5()
        self.progress_bar = ProgressBar(desc, not context.quiet)
        with requests.get(url, headers=headers, stream=True) as res:
            if res.headers.get("Accept-Ranges", "") != "bytes":
                if isfile(outpath):
                    os.remove(outpath)
                    offset = 0
            content_length = float(res.headers.get('Content-Length', 0))
            with open(outpath, "ab") as fo:
                for chunk in res.iter_content(chunk_size=2 ** 14):
                    if chunk:
                        offset += len(chunk)
                        fo.write(chunk)
                        md5.update(chunk)
                        self.progress_bar.update_to(offset/content_length)
        actual_checksum = md5.hexdigest()
        if actual_checksum != axn.md5:
            LOCAL_CONDA_LOG.debug("md5 mismatch for download: %s (%s != %s)",
                                  url, actual_checksum, axn.md5)
            raise ChecksumMismatchError(
                url, target_full_path, "md5", axn.md5, actual_checksum
            )
        actual_size = os.path.getsize(outpath)
        if actual_size != size:
            LOCAL_CONDA_LOG.debug("size mismatch for download: %s (%s != %s)",
                                  url, actual_size, size)
            raise ChecksumMismatchError(
                url, target_full_path, "size", size, actual_size)
        with self.lock:
            self.target_package_cache._urls_data.add_url(url)

    def run(self):
        try:
            self.download()
        except Exception as e:
            self.axn.reverse()
            return e
        else:
            self.axn.cleanup()
            self.progress_bar.finish()
        finally:
            self.progress_bar.close()


class Extract(object):
    def __init__(self, exn):
        self.exn = exn
        exn.verify()
        self.target_pkgs_dir = exn.target_pkgs_dir
        os.makedirs(self.target_pkgs_dir, exist_ok=True)
        self.target_package_cache = PackageCacheData(self.target_pkgs_dir)

    def extract(self):
        exn = self.exn
        if lexists(exn.target_full_path):
            rm_rf(exn.target_full_path)
        extract_tarball(exn.source_full_path, exn.target_full_path)
        try:
            raw_index_json = read_index_json(exn.target_full_path)
        except (IOError, OSError, JSONDecodeError, FileNotFoundError):
            print("ERROR: Encountered corrupt package tarball at %s. Conda has "
                  "left it in place. Please report this to the maintainers "
                  "of the package." % exn.source_full_path)
            sys.exit(1)
        if isinstance(exn.record_or_spec, MatchSpec):
            url = exn.record_or_spec.get_raw_value('url')
            assert url
            channel = Channel(url) if has_platform(
                url, context.known_subdirs) else Channel(None)
            fn = basename(url)
            sha256 = exn.sha256 or compute_sha256sum(exn.source_full_path)
            size = getsize(exn.source_full_path)
            if exn.size is not None:
                assert size == exn.size, (size, exn.size)
            md5 = exn.md5 or compute_md5sum(exn.source_full_path)
            repodata_record = PackageRecord.from_objects(
                raw_index_json, url=url, channel=channel, fn=fn, sha256=sha256, size=size, md5=md5,
            )
        else:
            repodata_record = PackageRecord.from_objects(
                exn.record_or_spec, raw_index_json)
        repodata_record_path = join(
            exn.target_full_path, 'info', 'repodata_record.json')
        write_as_json_to_file(repodata_record_path, repodata_record)
        package_cache_record = PackageCacheRecord.from_objects(
            repodata_record,
            package_tarball_full_path=exn.source_full_path,
            extracted_package_dir=exn.target_full_path,
        )
        self.target_package_cache.insert(package_cache_record)

    def run(self):
        try:
            self.extract()
        except Exception as e:
            self.exn.reverse()
            return e
        else:
            self.exn.cleanup()
