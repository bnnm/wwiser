<div class="field">
    ${if 'offset' in attrs: }
    <div class="offset">
        ${"%08x" % attrs['offset']}
    </div>
    ${:}
    <div class="head">
        <span class="attr type">${attrs['type']}</span>
        <span class="attr name">${attrs['name']}</span>
        ${ 
            if 'valuefmt' in attrs: 
                val = attrs['valuefmt']
            else:
                val = attrs['value']
        }
        <span class="attr value">${val}</span>

        ${ #clickable links need text nodes, but not anchors }
        ${if attrs['type'] == 'tid' and attrs['value'] > 0: }
            <a class="target" href="#${attrs['value']}">target</a>
        ${:}
        ${if attrs['type'] == 'sid': }
            <a class="anchor" id="${attrs['value']}" href="#${attrs['value']}">anchor</a>
        ${:}

        ${if 'hashname' in attrs: }<span class="attr hashname">(${attrs['hashname']})</span>${:}
        ${if 'guidname' in attrs: }<span class="attr guidname">{${attrs['guidname']}}</span>${:}
        ${if 'objpath' in attrs: }<span class="tooltip objpath"><span class="attr objpath">${attrs['objpath']}</span></span>${:}
        ${if 'path' in attrs: }<span class="tooltip path"><span class="attr path">${attrs['path']}</span></span>${:}
    </div>
    <div class="body">
        ${body}
    </div>
</div>
