import os
import sysconfig

from setuptools import setup
from functools import partial
from setuptools.extension import Extension


class Packages(object):

    def __init__(self, pkg_name=""):
        self.name = pkg_name
        self.base_dir = os.path.dirname(__file__)
        basejoin = partial(self._join, self.base_dir)
        self.source_dir = basejoin("src")
        self.version_file = basejoin("src/_version.py")
        self.des_file = basejoin("README.md")
        self.req_file = basejoin("requirements.txt")

    def _join(self, *args):
        return os.path.join(*args)

    @property
    def listdir(self):
        df, nc = [], []
        if os.path.isdir(self.name):
            for d, _, fs in os.walk(self.name):
                for f in fs:
                    ncf = self._join(d, f)
                    nc.append(self.source_dir + ncf[len(self.name):])
        for a, b, c in os.walk(self.source_dir):
            if os.path.basename(a).startswith("__"):
                continue
            for i in c:
                if i.startswith("__") or not i.endswith(".py") or self._join(a, i) in nc:
                    continue
                p = self._join(a[len(self.source_dir)+1:], i)
                df.append(p)
        return df

    @property
    def description(self):
        des = ""
        with open(self.des_file) as fi:
            des = fi.read()
        return des

    @property
    def version(self):
        v = {}
        with open(self.version_file) as fi:
            c = fi.read()
        exec(compile(c, self.version_file, "exec"), v)
        return v["__version__"]

    @property
    def requirements(self):
        requires = []
        with open(self.req_file) as fi:
            for line in fi:
                line = line.strip()
                requires.append(line)
        return requires

    @property
    def _extensions(self):
        exts = []
        for f in self.listdir:
            e = Extension(self.name + "." + os.path.splitext(f)[0].replace("/", "."),
                          [self._join(self.source_dir, f), ], extra_compile_args=["-O3", ],)
            e.cython_directives = {
                'language_level': sysconfig._PY_VERSION_SHORT_NO_DOT[0]}
            exts.append(e)
        return exts

    @property
    def _package_dir(self):
        pd = {}
        for a, b, v in os.walk(self.source_dir):
            p = a.replace(self.source_dir, self.name).replace("/", ".")
            pd[p] = a.replace(self.source_dir, "src")
        return pd

    def install(self, ext=False):
        kwargs = {}
        kwargs.update(
            name=self.name,
            version=self.version,
            packages=list(self._package_dir.keys()),
            license="MIT",
            url="https://github.com/yodeng/conda-local",
            package_dir=self._package_dir,
            package_data={self.name: ["*.ini", ]},
            install_requires=self.requirements,
            python_requires=">=3.5",
            long_description=self.description,
            long_description_content_type='text/markdown',
            entry_points={'console_scripts': self._entrys},
        )
        if ext:
            kwargs.pop("package_dir")
            kwargs["ext_modules"] = self._extensions
        setup(**kwargs)

    @property
    def _entrys(self):
        eps = [
            '%s = %s.main:main' % (self.name.replace("_", "-"), self.name),
        ]
        return eps


def main():
    pkgs = Packages("conda_local")
    pkgs.install(ext=False)


if __name__ == "__main__":
    main()
