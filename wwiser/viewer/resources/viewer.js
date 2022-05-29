// server interaction util
function Viewer() {
    this.load_banks = load_banks;
    this.load_banks_all = load_banks_all;
    this.load_simple = load_simple;
    this.load_simple_all = load_simple_all;
    this.load_node = load_node;
    this.load_docs_readme = load_docs_readme;
    this.load_docs_wwiser = load_docs_wwiser;


    function load_banks(on_success) {
        get_ajax('/load-banks', on_success);
    }
    function load_banks_all(on_success) {
        get_ajax('/load-banks?all=true', on_success);
    }
    function load_simple(on_success) {
        get_ajax('/load-banks?simple=true', on_success);
    }
    function load_simple(on_success) {
        get_ajax('/load-banks?simple=true', on_success);
    }
    function load_simple_all(on_success) {
        get_ajax('/load-banks?all=true&simple=true', on_success);
    }
    function load_node(id, on_success) {
        get_ajax('/load-node?id='+id, on_success);
    }
    function load_docs_readme(on_success) {
        get_ajax('/load-docs?doc=readme', on_success);
    }
    function load_docs_wwiser(on_success) {
        get_ajax('/load-docs?doc=wwiser', on_success);
    }

    function get_ajax(url, on_success, on_error) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);

        xhr.onload = function() {
            if (this.status >= 200 && this.status < 400) {
                on_success(this.response);
            } else {
                do_error();
            }
        };
        xhr.onerror = do_error
        xhr.send();

        function do_error() {
            if (on_error) {
                on_error();
            } else {
                alert("Viewer stopped (restart wwiser's viewer)")
            }
        }
    }
}


// view namespace
(function() {
    var NODE_WARNING_MAX = 300;
    var NODE_WARNING_MSG = "Warning! Preload size is big and may be slow/unresponsive!";
    var NODE_EMPTY_MSG = "No nodes found";

    var viewer = new Viewer();

    var $d = document;
    var $tabs_panel = $d.getElementById('tabs-panel');
    var $tabs = $d.getElementById('tabs');
    var vbank = load_view('tab-bank');
    var vsimple = load_view('tab-simple');
    var vdocs_readme = load_view('tab-docs-readme');
    var vdocs_wwiser = load_view('tab-docs-wwiser');

    setup();
    init();
    //todo capture clicked 'tid' and find object's sid in server if not open

    /* *************************** */

    function init() {
        vbank.tab.click()
    }

    function load_view(id_name) {
        var v =  {};
        v.button = $tabs_panel.querySelector('[for='+id_name+']')
        v.tab = $d.getElementById(id_name);
        v.main = v.tab.nextElementSibling;
        v.tools = v.main.querySelector('.tools');
        v.content = v.main.querySelector('.content');
        v.loaded = false;
        return v;
    }

    function load_items(view, res) {
        view.content.innerHTML = res;
        view.loaded = true;
    }
    function set_active(view, loader) {
        //todo query selector etc
        var elems = $tabs_panel.querySelectorAll('.tab-button');
        elems.forEach(button => console.log(button));
        elems.forEach(button => button.classList.remove('selected'));
        view.button.classList.add('selected')
        if (view.loaded)
            return;
        loader(function(res) {
            load_items(view, res);
        });
    }

    function setup() {
        var items = [
            [vbank, viewer.load_banks],
            [vsimple, viewer.load_simple],
            [vdocs_readme, viewer.load_docs_readme],
            [vdocs_wwiser, viewer.load_docs_wwiser]
        ];

        // tab changes
        $tabs.addEventListener('click', function(e) {
            var tgt = e.target;
            if (!tgt)
                return;

            for (var i = 0; i < items.length; i++) {
                var obj = items[i][0];
                var fun = items[i][1];

                if (tgt == obj.tab) {
                    set_active(obj, fun);
                    return;
                }
            }

        }, false);


        // viewer main functions
        vbank.main.addEventListener('click', function(e) {
            var tgt = e.target;
            if (!tgt)
                return;

            if (tgt.matches('.hide')) {
                vbank.main.classList.toggle(tgt.value);
            }

            if (tgt.matches('.load-all')) {
                var filter = vbank.tools.querySelector('.load-type').value;
                var selector = '.js-load-node';
                if (filter)
                    selector += '.'+filter;

                var elems = vbank.content.querySelectorAll(selector);
                if (elems.length > NODE_WARNING_MAX) {
                    if (!window.confirm(NODE_WARNING_MSG))
                        return;
                }

                if (elems.length == 0) {
                    alert(NODE_EMPTY_MSG);
                    return;
                }

                if (filter) {
                    for (var i = 0; i < elems.length; i++) {
                        elems[i].querySelector('.head').click();
                    }
                }
                else {
                    viewer.load_banks_all(function(res) {
                        load_items(vbank, res);
                    });
                }

                return;
            }

            if (tgt.matches('.closable > .head')) {
                var obj = tgt.parentNode;
                if (obj.matches('.js-load-node')) {
                    id = obj.dataset.id;
                    viewer.load_node(id, function(res) {
                        obj.outerHTML = res;
                        //obj.classList.toggle('hidden');
                        //TODO: may need to evict DOM nodes if there are too many open to improve performance
                    });
                } else {
                    obj.classList.toggle('hidden');
                }
                return;
            }

        }, false);

    }

})();
