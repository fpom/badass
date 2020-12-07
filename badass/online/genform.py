import yaml

class _Form (object) :
    def __init__ (self, ident, title=None) :
        self.ident = ident
        self.title = title
        self.parent = None
        self.children = []
    @property
    def base (self) :
        path = [self.ident]
        up = self.parent
        while up is not None :
            path.append(up.ident)
            up = up.parent
        return "_".join(reversed(path))
    def __iter__ (self) :
        return iter(self.children)
    def append (self, child) :
        self.children.append(child)
        if isinstance(child, _Form) :
            child.parent = self

class Select (_Form) :
    def __init__ (self, chose, ident, title=None) :
        super().__init__(ident, title)
        self.chose = chose
    def __call__ (self, out) :
        out.write(f'function mk_{self.base} () {{\n'
                  f'  $("#form").append("<select id=\'{self.ident}\' name=\'{self.ident}\'>\\\n'
                  f'    <option disabled selected value>-- {self.chose} --</option>\\\n')
        for child in self :
            out.write(f'    <option value=\'{child.ident}\'>{child.title}</option>\\\n')
        out.write(f'    </select>");\n'
                  f'  $("#{self.ident}").change(on_{self.base});\n'
                  f'}}\n\n'
                  f'function on_{self.base} () {{\n'
                  f'  $("#{self.ident}").nextAll().remove();\n'
                  f'  jQuery.globalEval("mk_{self.base}_"'
                  f' + $("#{self.ident}").val() + "();");\n'
                  f'}}\n\n');
        for child in self :
            child(out)
        if self.title is None :
            out.write(f'$(document).ready(mk_{self.base});\n')

class Form (_Form) :
    def __call__ (self, out) :
        out.write(f'function mk_{self.base} () {{\n'
                  f'  $("#form").append(')
        for i, child in enumerate(self) :
            if i :
                out.write(f'    "{child}",\n')
            else :
                out.write(f'"{child}",\n')
        out.write('    "<input type=\'submit\' value=\'Submit\'>");\n');
        out.write(f'}}\n\n')

def first (data) :
    assert type(data) is dict, repr(data)
    assert len(data) == 1
    key, val = next(iter(data.items()))
    return key.replace(" ", "_"), val

class Loader (object) :
    def load (self, stream) :
        data = yaml.load(stream, Loader=yaml.FullLoader)
        ret = Select("course", "Course")
        for course in data :
            ret.append(self._load(course))
        return ret
    def _load (self, data, fields=[], path=[]) :
        ident, content = first(data)
        attr = {"ident" : ident}
        fields = list(fields)
        path = list(path)
        children = []
        for child in content :
            key, val = first(child)
            if key in ("title", "chose") :
                attr[key] = val
            elif key == "path" :
                path.append(val)
            elif key == "form" :
                fields.extend(self._load_form(val))
            else :
                children.append(self._load(child, fields, path))
        if "chose" in attr :
            ret = Select(**attr)
            for child in children :
                ret.append(child)
        else :
            ret = Form(**attr)
            path = "/".join(path)
            ret.append(f"<input type='hidden' name='path' value='{path}'>")
            for field in fields :
                ret.append(field)
        return ret
    def _load_form (self, fields) :
        for field in fields :
            tag, content = first(field)
            attr = []
            text = None
            children = []
            for d in content :
                k, v = first(d)
                if k == "text" :
                    text = v
                elif isinstance(v, list) :
                    children.extend(self._load_form([d]))
                else :
                    attr.append((k, v))
            html = " ".join(f"{k}='{v}'" for k, v in attr)
            if children :
                inner = "".join(children)
                yield f'<{tag} {html}>{inner}</{tag}>'
            elif text :
                yield f'<{tag} {html}>{text}</{tag}>'
            else :
                yield f'<{tag} {html}>'

if __name__ == "__main__" :
    import argparse, sys
    parser = argparse.ArgumentParser("genform")
    parser.add_argument("-o", "--output", metavar="PATH",
                        type=argparse.FileType(mode="w", encoding="utf-8"),
                        default=sys.stdout,
                        help="output JS to PATH")
    parser.add_argument("input", metavar="PATH",
                        type=argparse.FileType(mode="r", encoding="utf-8"),
                        help="input YAML from PATH")
    args = parser.parse_args()
    loader = Loader()
    form = loader.load(args.input)
    form(args.output)
