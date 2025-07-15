###
#  code snippet rendering utilities
###

# This makes the html safe by default,
# so you don't have to pass "| safe"
# whenever you call .place_code()
from markupsafe import Markup
# TODO: remove annoying white space at the end of code box

class CodeSnippet():
    """ Utility class for displaying code snippets on lmfdb pages
    """
    def __init__(self, code, item=None, pre="", post=""):
        self.code = code
        self.item = item
        self.langs = sorted([lang for lang in code['show']])
        self.pre, self.post = pre, post
                
    def place_code(self):
        """Return HTML string which displays code in code box, with copying functionality."""
        if self.item is None:
            raise ValueError("No code to place, please init with code item")
        item = self.item 
        # replaces jinja macro place_code 
        snippet_str = self.pre # initiate new string
        prompt_style = "color: gray;"
        code_style = "user-select: text; flex: 1"
        code = self.code
        if code[item]:
            for L in code[item]:
                if isinstance(code[item][L],str):
                    lines = code[item][L].split('\n')[:-1] if '\n' in code[item][L] else [code[item][L]]
                    lines = [line.replace("<", "&lt;").replace(">", "&gt;") for line in lines]
                else:   
                    lines = code[item][L]

                prompt = code['prompt'][L] if 'prompt' in code and L in code['prompt'] else L
                class_str = " ".join([L,'nodisplay','codebox'])
                sep = "\n"
                snippet_str += f"""
    <div class="{class_str}" style="user-select: none; margin-bottom: 12px; align-items: top">
        <span class="raw-tset-copy-btn" onclick="copycode(this)" style="max-height: 12px; margin: 3px"><img alt="Copy content" class="tset-icon"></span> 
        <span class="prompt" style="{prompt_style}">{prompt}:&nbsp;</span><span class="code" style="{code_style}">{sep.join(lines)}</span>
        <div style="margin: 0; padding: 0; height: 0;">&nbsp;</div>
    </div>
    """
        return Markup(snippet_str + self.post)

    def show_commands_box(self):
        """Display 'Show commands' box and corresponding logic"""
        lang_names = {"pari": "PariGP", "sage": "SageMath", "magma": "Magma", "oscar": "Oscar"}
        box_str = r"""<div align="right" style="float: right; margin-top:2px;">""" + "Show commands: "
        lang_strs = []
        for lang in self.langs:
            name = lang_names[lang] if lang in lang_names.keys() else lang
            lang_strs.append(rf"""<a onclick="show_code('{lang}',{self.langs} ); return false" href='#'>{name}</a>""")

        box_str += " / ".join(lang_strs) + "</div>"
        # NB: unlike the past jinja2 macro, this formats as inline-flex 
        # instead of inline-block in order to correctly render copy symbol in blocks
        js_str = r"""
        <script>
        var cur_lang = null;
        function show_code(new_lang, langs) {
           for(var lang of langs){$('.'+lang).hide()}
            if (cur_lang == new_lang) {
              cur_lang = null;
            } else {
              $('.'+new_lang).show();
              $('.'+new_lang).css('display','inline-flex');
              cur_lang = new_lang;
            }
        }
        </script>
        """
        return js_str + box_str
    
