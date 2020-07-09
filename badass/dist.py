import pathlib, os
import lzma, bz2, zlib
import chardet
import pandas as pd
import seaborn as sns
import matplotlib.pylab as plt

from scipy.cluster.hierarchy import ClusterWarning, to_tree, linkage
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
    @classmethod
    def read_csv (cls, path, algo="lzma") :
        data = pd.read_csv(path, index_col=0)
        data.index = data.index.astype(str)
        self = cls([], algo)
        self.dist = data
        return self
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
    def _read (self, path) :
        raw = path.open("rb").read()
        enc = chardet.detect(raw)
        return raw.decode(enc["encoding"] or "ascii", errors="replace")
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
                        data.append(self._read(child))
        else :
            data.append(self._read(path))
        return "".join(data).encode("utf-8", errors="replace")
    def csv (self, out) :
        self.dist.to_csv(out)
    def _leaves (self, node) :
        if node.is_leaf() :
            return self.dist.index[node.get_id()]
    def heatmap (self, path, max_size=0, absolute=False, **args) :
        kw_lnk = {}
        kw_sns = {"vmax" :1.0 if absolute else self.dist.max().max(),
                  "cmap" : "RdYlBu"}
        kw_plt = {}
        kw = {"lnk" : kw_lnk, "sns" : kw_sns, "plt" : kw_plt}
        for key, val in args.items() :
            if key[:3] in kw and key[3:4] == "_" :
                kw[key[:3]][key[4:]] = val
            else :
                raise TypeError(f"unexpected argument {key!r}")
        # draw whole heatmap
        data = self.dist.fillna(0)
        link = linkage(data, **kw_lnk)
        cg = sns.clustermap(data, row_linkage=link, col_linkage=link, **kw_sns)
        plt.setp(cg.ax_heatmap.yaxis.get_majorticklabels(), rotation=0)
        plt.setp(cg.ax_heatmap.xaxis.get_majorticklabels(), rotation=90)
        cg.savefig(path, **kw_plt)
        plt.close(cg.fig)
        if not max_size :
            return
        # split dendogram into subtrees
        todo = [to_tree(cg.dendrogram_row.calculated_linkage)]
        done = []
        while todo :
            tree = todo.pop()
            if tree.get_count() > max_size :
                todo.extend([tree.left, tree.right])
            else :
                done.append(tree)
        # draw each subtree
        path = pathlib.Path(path)
        base = path.parent
        name = path.with_suffix("").name
        sufx = path.suffix
        for num, tree in enumerate(done) :
            target = str(base / f"{name}-{num}{sufx}")
            leaves = set(tree.pre_order(self._leaves)) - {None}
            dist = self.dist[self.dist.index.isin(leaves)][[str(l) for l in leaves]]
            if len(dist) <= 1 :
                continue
            sub = sns.clustermap(dist.fillna(0), **kw_sns)
            plt.setp(sub.ax_heatmap.yaxis.get_majorticklabels(), rotation=0)
            plt.setp(sub.ax_heatmap.xaxis.get_majorticklabels(), rotation=90)
            sub.savefig(target, **kw_plt)
            plt.close(sub.fig)
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
