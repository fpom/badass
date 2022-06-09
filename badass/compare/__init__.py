import pathlib, os
import lzma, bz2, zlib
import chardet
import pandas as pd
import numpy as np

class Dist (object) :
    def __init__ (self, keys, algo="lzma") :
        try :
            self.c = getattr(self, "_c_" + algo)
        except AttributeError :
            raise ValueError(f"unsupported compression '{algo}'")
        self.size = pd.DataFrame(index=keys, columns=keys)
        self.dist = pd.DataFrame(index=keys, columns=keys)
    def __len__ (self) :
        return len(self.dist.index)
    @classmethod
    def _size_path (cls, path) :
        p = pathlib.Path(path)
        return (p.parent / (p.stem + "-size")).with_suffix(".csv")
    @classmethod
    def _load_csv (cls, keys, path) :
        data = pd.read_csv(path, index_col=0)
        data.index = data.index.astype(str)
        data.columns = data.columns.astype(str)
        if drop := list(set(data.columns) - set(keys)) :
            data.drop(columns=drop, inplace=True)
        if drop := list(set(data.index) - set(keys)) :
            data.drop(index=drop, inplace=True)
        if more := list(set(keys) - set(data.columns)) :
            data.loc[:,more] = float("nan")
        if more := list(set(keys) - set(data.index)) :
            other = pd.DataFrame(index=more, columns=data.columns)
            data = data.append(other)
        return data
    @classmethod
    def read_csv (cls, keys, path, algo="lzma") :
        self = cls([], algo)
        self.dist = self._load_csv(keys, path)
        self.size = self._load_csv(keys, self._size_path(path))
        return self
    def csv (self, out) :
        self.dist.to_csv(out)
        try :
            out_name = out.name
        except :
            out_name = str(out)
        self.size.to_csv(self._size_path(out_name))
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
    def _leaves (self, node) :
        if node.is_leaf() :
            return self.dist.index[node.get_id()]
    def heatmap (self, path, max_size=0, prune=0, absolute=False, **args) :
        import seaborn as sns
        import matplotlib.pylab as plt
        from scipy.cluster.hierarchy import to_tree, linkage, ClusterWarning
        from warnings import simplefilter
        simplefilter("ignore", ClusterWarning)
        path = pathlib.Path(path)
        kw_lnk = {}
        kw_sns = {"vmax" : 1.0 if absolute else self.dist.max().max(),
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
        link = linkage(data.values[np.triu_indices(len(self.dist), 1)], **kw_lnk)
        cg = sns.clustermap(data, row_linkage=link, col_linkage=link, **kw_sns)
        plt.setp(cg.ax_heatmap.yaxis.get_majorticklabels(), rotation=0)
        plt.setp(cg.ax_heatmap.xaxis.get_majorticklabels(), rotation=90)
        cg.savefig(path, **kw_plt)
        plt.close(cg.fig)
        # prune outliers
        tree = to_tree(cg.dendrogram_row.calculated_linkage)
        if prune and tree.dist :
            leaves = set()
            if 0 < prune < 1 :
                todo = [tree]
                while todo :
                    node = todo.pop()
                    if node.dist / tree.dist <= prune :
                        if node.get_count() > 1 :
                            leaves.update(node.pre_order(self._leaves))
                    else :
                        if node.left :
                            todo.append(node.left)
                        if node.right :
                            todo.append(node.right)
            elif prune > 1 :
                forest = [tree]
                def sort_key (node) :
                    return node.dist, -node.get_count()
                while sum(node.get_count() for node in forest) > prune :
                    node = forest.pop(-1)
                    for child in (node.left, node.right) :
                        if child and child.get_count() > 1 :
                            forest.append(child)
                    forest.sort(key=sort_key)
                for node in forest :
                    leaves.update(node.pre_order(self._leaves))
            leaves.discard(None)
            if len(leaves) > 1 :
                _kw = kw_sns.copy()
                if len(leaves) < 55 :
                    _kw.setdefault("xticklabels", 1)
                    _kw.setdefault("yticklabels", 1)
                dist = self.dist[self.dist.index.isin(leaves)][[str(l) for l in leaves]]
                sub = sns.clustermap(dist.fillna(0), **_kw)
                plt.setp(sub.ax_heatmap.yaxis.get_majorticklabels(), rotation=0)
                plt.setp(sub.ax_heatmap.xaxis.get_majorticklabels(), rotation=90)
                target = str(path.parent / f"{path.stem}-pruned{path.suffix}")
                sub.savefig(target, **kw_plt)
                plt.close(sub.fig)
        # split dendogram into subtrees
        if not max_size :
            return
        todo = [tree]
        done = []
        while todo :
            tree = todo.pop()
            if tree.get_count() > max_size :
                todo.extend([tree.left, tree.right])
            else :
                done.append(tree)
        # draw each subtree
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
        if not (pd.isna(self.size.loc[k1][k1])
                or pd.isna(self.size.loc[k2][k2])
                or pd.isna(self.size.loc[k1][k2])
                or pd.isna(self.size.loc[k2][k1])) :
            return
        d1 = d2 = None
        if not pd.isna(self.size.loc[k1][k1]) :
            s1 = self.size.loc[k1][k1]
        else :
            d1 = self._load(p1, glob)
            s1 = self.size.loc[k1][k1] = self.c(d1)
        if s1 == 0 :
            self.dist.drop(index=k1, columns=k1, inplace=True, errors="ignore")
            return
        if not pd.isna(self.size.loc[k2][k2]) :
            s2 = self.size.loc[k2][k2]
        else :
            d2 = self._load(p2, glob)
            s2 = self.size.loc[k2][k2] = self.c(d2)
        if s2 == 0 :
            self.dist.drop(index=k2, columns=k2, inplace=True, errors="ignore")
            return
        if not pd.isna(self.size.loc[k1][k2]) :
            s3 = self.size.loc[k1][k2]
        else :
            if d1 is None :
                d1 = self._load(p1, glob)
            if d2 is None :
                d2 = self._load(p2, glob)
            s3 = self.size.loc[k1][k2] = self.size.loc[k2][k1] = self.c(d1 + d2)
        d = 1 - (s1 + s2 - s3) / max(s1, s2)
        self.dist.loc[k1][k2] = self.dist.loc[k2][k1] = d
