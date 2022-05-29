
#ugly markdown-to-html converter, don't do this at home
# doesn't support urls, lists-in-lists or more complex stuff

class Markdown(object):

    def convert(self, text):
        mlines = text.splitlines()
        lines = []


        is_p = False
        is_ul = False
        is_li = False
        is_pre = False
        is_pre_first = False

        lines.append('<div class="doc markdown">')
        for line in mlines:
            #header
            if not is_pre:
                if   line.startswith('#'):
                    if   line.startswith('###'):
                        lines.append('<h3>%s</h3>' % (line[3:]))
                    elif line.startswith('##'):
                        lines.append('<h2>%s</h3>' % (line[2:]))
                    elif line.startswith('#'):
                        lines.append('<h1>%s</h1>' % (line[1:]))
                    continue


            #start paragraph or more text
            if   line:
                if   line.startswith('```'):
                    if not is_pre:
                        is_pre = True
                        is_pre_first = True
                        lines.append('<pre>')#<pre><code>
                        line = line[3:]
                    else:
                        is_pre = False
                        lines.append('</pre>')#</code></pre>
                        line = line[3:]
                elif is_pre:
                    pass
  
                #list start
                elif line.startswith('-'):
                    line = line[1:]
                    if not is_ul:
                        is_ul = True
                        lines.append('<ul>')
                    if is_li:
                        lines.append('</li>')
                    lines.append('<li>')
                    is_li = True
  
                #list continue
                elif line.startswith(' ') and is_li:
                    pass
                #paragraph and/or list end
                elif is_p:
                    if not line.startswith(' '):
                        lines.append(' ') #extra word after line breaks
                elif not is_p:
                    if is_li:
                        is_li = False
                        is_ul = False
                        lines.append('</li></ul>')
                    is_p = True
                    lines.append('<p>')

            #end paragraph
            elif not line:
                if is_p:
                    is_p = False
                    lines.append('</p>')
                if is_li:
                    is_li = False
                    is_ul = False
                    lines.append('</li></ul>')

            #modifiers
            if not is_pre:
                line = self.replacer(line, '**', '<b>', '</b>')
                line = self.replacer(line, '*', '<i>', '</i>')
                line = self.replacer(line, '`', '<code>', '</code>')

            lines.append(line)
            if is_pre:
                if not is_pre_first:
                    lines.append('<br/>')
                is_pre_first = False

        lines.append('</div>')

        msg = ''.join(lines)
        return msg


    def replacer(self, line, find, repl1, repl2):
        if not line:
            return line

        if line.count(find) % 2 != 0: #only in pairs
            return line

        #maybe some regex but multiple are possible
        is_open = False
        while find in line:
            if not is_open:
                repl = repl1
            else:
                repl = repl2
            line = line.replace(find, repl, 1)
            is_open = not is_open

        return line
