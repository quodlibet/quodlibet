# An example plugin that fixes Shift-JIS misinterpreted as Latin 1.

from plugins.editing import EditTagsPlugin

class SJISFix(EditTagsPlugin):
    def __init__(self, tag, value):
        super(SJISFix, self).__init__(_("Convert from Shift-JIS"))
        try: new = value.encode('latin1').decode('shift-jis')
        except: self.set_sensitive(False)
        else: self.set_sensitive(new != value)

    def activated(self, tag, value):
        return [(tag, value.encode('latin1').decode('shift-jis'))]
