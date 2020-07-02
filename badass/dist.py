import pathlib, os
import lzma, bz2, zlib
import pandas as pd
import seaborn as sb
import matplotlib.pylab as plt

from scipy.cluster.hierarchy import ClusterWarning
from warnings import simplefilter
simplefilter("ignore", ClusterWarning)

class Dist (object) :
    def __init__ (self, algo="lzma") :
        try :
            self.c = getattr(self, "_c_" + algo)
        except AttributeError :
            raise ValueError(f"unsupported compression '{algo}'")
        self.size = {}
        self.dist = pd.DataFrame()
    def _c_lzma (self, data) :
        return len(lzma.compress(data, preset=9))
    def _c_bz2 (self, data) :
        return len(bz2.compress(data, 9))
    def _c_zlib (self, data) :
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
        assert (k1,k2) not in self.dist
        assert (k1,k2) not in self.size
        if k1 in self.size :
            s1 = self.size[k1]
            d1 = self._load(p1, glob)
        else :
            d1 = self._load(p1, glob)
            s1 = self.size[k1] = self.c(d1)
        if k2 in self.size :
            s2 = self.size[k2]
            d2 = self._load(p2, glob)
        else :
            d2 = self._load(p2, glob)
            s2 = self.size[k2] = self.c(d2)
        s3 = self.c(d1 + d2)
        self.size[k1,k2] = self.size[k2,k1] = s3
        if k1 not in self.dist.columns :
            self.dist[k1] = None
            self.dist.loc[k1] = None
        if k2 not in self.dist.columns :
            self.dist[k2] = None
            self.dist.loc[k2] = None
        d = 1 - (s1 + s2 - s3) / max(s1, s2)
        self.dist.loc[k1,k2] = d
        self.dist.loc[k2,k1] = d
