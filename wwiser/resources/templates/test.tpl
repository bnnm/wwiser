TEMPLATE:
${ if _exists('none'):}
    none
${: else: }
    user: ${user}
${:}
    map: ${testmap['key']}
