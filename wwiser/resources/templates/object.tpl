<div class="object closable ${extra}" data-id="${id}">
    <div class="head">
        <span class="attr type">obj</span>
        <span class="attr name">
            ${attrs['name']}${if 'index' in attrs:}<span class="index">[${attrs['index']}]</span>${:}
        </span>
    </div>
    <div class="body">
        ${body}
    </div>
</div>
