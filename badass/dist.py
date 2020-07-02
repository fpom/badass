import pathlib, os
import lzma, bz2, zlib
import pandas as pd
import seaborn as sb
import matplotlib.pylab as plt

from scipy.cluster.hierarchy import ClusterWarning
from warnings import simplefilter
simplefilter("ignore", ClusterWarning)

class Dist (object) :
    def __init__ (self, keys, algo="lzma") :
        try :
            self.c = getattr(self, "_c_" + algo)
        except AttributeError :
            raise ValueError(f"unsupported compression '{algo}'")
        self.size = {}
        self.dist = pd.DataFrame(index=keys, columns=keys)
    def _c_lzma (self, data) :
        if not data :
            return 0
        else :
            return len(lzma.compress(data, preset=9))
    def _c_bz2 (self, data) :
        if not data :
            return 0
        else :
            return len(bz2.compress(data, 9))
    def _c_zlib (self, data) :
        if not data :
            return 0
        else :
            return len(zlib.compress(data, 9))
    def _load (self, path, glob) :
        if not glob :
            glob = ["*"]
        path = pathlib.Path(path)
        data = []
        if path.is_dir() :
            for dirpath, _, filenames in os.walk(path) :
                for name in filenames :
                    child = pathlib.Path(dirpath) / name
                    if any(child.match(p) for p in glob) :
                        data.append(child.open("rb").read())
        else :
            data.append(path.open("rb").read())
        return b"".join(data)
    def csv (self, out) :
        self.dist.to_csv(out)
    def heatmap (self, path) :
        cg = sb.clustermap(self.dist.fillna(0), cmap="RdYlBu")
        plt.setp(cg.ax_heatmap.yaxis.get_majorticklabels(), rotation=0)
        plt.setp(cg.ax_heatmap.xaxis.get_majorticklabels(), rotation=90)
        cg.savefig(path)
    def add (self, k1, p1, k2, p2, *glob) :
        d1 = self._load(p1, glob)
        if k1 in self.size :
            s1 = self.size[k1]
        else :
            s1 = self.size[k1] = self.c(d1)
        if s1 == 0 :
            self.dist.drop(index=k1, columns=k1, inplace=True, errors="ignore")
            return
        d2 = self._load(p2, glob)
        if k2 in self.size :
            s2 = self.size[k2]
        else :
            s2 = self.size[k2] = self.c(d2)
        if s2 == 0 :
            self.dist.drop(index=k2, columns=k2, inplace=True, errors="ignore")
            return
        s3 = self.c(d1 + d2)
        d = 1 - (s1 + s2 - s3) / max(s1, s2)
        self.dist.loc[k1][k2] = self.dist.loc[k2][k1] = d
