<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="#stylesheet" ?>
<!DOCTYPE doc [
  <!ELEMENT xsl:stylesheet (#PCDATA)>
  <!ATTLIST xsl:stylesheet id ID #REQUIRED>
]>
<doc>

<!-- STYLESHEET -->
<xsl:stylesheet id="stylesheet" version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" >
    <!-- HTML5 doctype -->
    <xsl:output method="html" indent="yes" encoding="UTF-8" doctype-system="about:legacy-compat" />

    <!-- ignore space text nodes -->
    <xsl:strip-space elements="*"/>

    <!-- do nothing for this stylesheet -->
    <xsl:template match="xsl:stylesheet" />

    <!-- make root node base HTML -->
    <xsl:template match="/doc/base"> 
        <html>
            <head>
                <title>wwiser dump</title>
                <style>
html { overflow-y: scroll; }
body { font-family: monospace; font-size: 16px; white-space: nowrap; }

/* fields */
.object, .list, .field, .skip, .error { margin-left: 45px; }

.head { display: flex;  align-items: center; }
.head > .attr { _margin-right:10px; _display:inline-block; margin: 0; padding: 0; _outline: 1px solid red;}
.head > .attr.type { min-width:45px; color:#0074D9; }
.head > .attr.name { min-width:350px; color:#FF4136; }
.head > .attr.value { color:#3D9970; }
.head > .attr.hashname,
.head > .attr.guidname,
.head > .attr.objpath,
.head > .attr.path { color:#800080; _color:#9932CC; margin-left:10px; }

.list > .head > .attr { color:#B10DC9; }
.object > .head > .attr.name { width:auto; }
.object > .head > .attr.type,
.object > .head > .attr.name { color:#85144b; }

.index { color:#777; font-size:12px; }
.skip { color: #777; } 
.error { color:red; font-weight: bold; }
.error:before { content: '**'; }

.offset { color: #aaa; position: absolute; left: 10px; }
.content { margin-left:80px; }

/* simple */
.simple .head > .attr.type { display:none; }
.simple .offset { display:none; }

/* links */
.target {
    display:inline-block; width:0px; height:0px; min-width:0px;max-width:0px; min-height:0px;max-height:0px; vertical-align: center;
    margin-left:6px;text-indent:16px; overflow: hidden;
    background-color: transparent;  border-radius:1px; width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 10px solid cadetblue;
}
.anchor {
    display:inline-block; width:10px; height:10px; min-width:10px;max-width:10px; min-height:10px;max-height:10px; vertical-align: center;
    margin-left:6px; text-indent:16px; overflow: hidden;
    background-color: #87b6b8; border-radius:6px;
}

/* toggler */
.closable > .head { cursor:pointer; margin-left: -25px; padding-left: 25px; }
.closable > .head:before {
    content:'-'; position:absolute; font-weight: bold; margin-top:2px; margin-left: -25px; color:666; 
    width:20px; line-height:12px; text-align:center; display:inline-block; background-color:#eee; border-radius:3px; vertical-align: bottom;
}
.closable.hidden > .head:before { content:'+'; }
.closable > .head > .attr { cursor:auto; }
.closable.hidden > .body { display:none; }

/* tooltips */
.tooltip {
    position: relative;
    display: inline-block;
    background-color:#800080;
    width: 10px; height: 10px; margin-left:2px;
}
.tooltip.objpath { }
.tooltip.path { border-radius: 6px; }

.tooltip > .attr {
    display:none; position: absolute; top: -5px; right: 100%;
    border-radius: 5px; padding: 1px; background-color: #eee; color:#800080
}
.tooltip:hover .attr {
    display:block;
}

/* page */
.tools {
    border: 1px solid #ccc;
    border-radius: 5px;
    padding: 10px;
    margin-bottom: 30px;
}
.view.hide-offset .offset {
    display:none;
}
.view.hide-type .attr.type {
    display:none;
}

                </style>
            </head>
            <body>
                <div class="view" id="view">
                    <div class="tools">
                        Hide:
                        <label><input type="checkbox" class="hide" value="hide-offset"/>Offset</label>
                        <label><input type="checkbox" class="hide" value="hide-type"/>Type</label>
                    </div>
                    <div class="content">
                        <xsl:apply-templates />
                    </div>
                </div>

                <script>
<xsl:text disable-output-escaping="yes">
<![CDATA[
(function() {
    let main = document.getElementById('view');
    document.addEventListener('click', function(e) {
        if (!e.target)
            return;

        if (e.target.matches('.closable > .head')) {
            e.target.parentNode.classList.toggle('hidden');
            return;
        }
        if (e.target.matches('.hide')) {
            main.classList.toggle(e.target.value);
            return;
        }
    }, false);

    // test option to middle-click on a wem and open it, browser support is kinda wonky
    /*
    let NEW_VERSION = 62;
    let version = null;
    function get_version() {
        if (version)
            return version;

        let root_obj = document.querySelector('.root > .head > name');
        if (!root_obj)
            return null;
        version = int(root_obj.textContent.substring(1));
        return version;
    }

    function get_ext(source_obj) {
        let version = get_version();
        if (version >= NEW_VERSION )
            return '.wem';

        let plugin_fld = source_obj.querySelector('.head > .value');
        if (plugin_fld.textContent.includes('[VORBIS]'))
            return '.ogg';
        if (plugin_fld.textContent.includes('[XMA]'))
            return '.xma';
        return '.wav'
    }

    document.addEventListener('auxclick', function(event) {
        if (event.button != 1)
            return;

        let elem = event.target;
        if (!elem.matches('a.target'))
            return;

        event.preventDefault();

        let media_obj = elem.closest('.object'); //AkMediaInformation
        if (!media_obj)
            return;

        let obj_name = media_obj.querySelector('.head > .name');
        if (!obj_name.textContent.includes('AkMediaInformation'))
            return;
        let is_stream = false;
        let source_obj = media_obj.parentElement.closest('.object');
        let type_fld = media_obj.previousElementSibling;
        if (type_fld) {
            let type_value = type_fld.querySelector('.value');
            is_stream = type_value.textContent.includes('[Streaming]');
        }

        let elem_id = elem.href.substring(elem.href.lastIndexOf('#') + 1);

        if (is_stream) {
            let filename = elem_id + get_ext(source_obj);
            window.open(filename);
            //window.open('file://' + filename);
        }
        else {
            //would need to detect subsong N + pass TXTP to browser
        }
    })
    */

})();
]]>
</xsl:text>
                </script>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="root">
        <div class="root closable">
            <div class="head">
                <span class="attr type">bank</span>
                <span class="attr name">v<xsl:value-of select="@version"/></span>
                <span class="attr value"><xsl:value-of select="@filename"/></span>
                <!--<span class="attr value">(<xsl:value-of select="@path"/></span>-->
            </div>
            <div class="body">
                <xsl:apply-templates />
            </div>
        </div>
    </xsl:template>

    <xsl:template match="object|obj">
        <div class="object closable">
            <div class="head">
                <span class="attr type">obj</span>
                <span class="attr name">
                    <xsl:value-of select="@name|@na"/>
                    <xsl:if test="@index|@ix">
                        <span class="index">[<xsl:value-of select="@index|@ix"/>]</span>
                    </xsl:if>
                </span>
            </div>
            <div class="body">
                <xsl:apply-templates />
            </div>
        </div>
    </xsl:template>

    <xsl:template match="list|lst">
        <!--<xsl:if test="count(*)>0">-->
        <div class="list closable">
            <div class="head">
                <span class="attr type">list</span>
                <span class="attr name"><xsl:value-of select="@name|@na"/></span>
                <span class="attr value"><xsl:value-of select="@count|@co"/></span>
            </div>
            <div class="body">
                <xsl:apply-templates />
            </div>
        </div>
        <!--</xsl:if>-->
    </xsl:template>

    <xsl:template match="field|fld">
        <div class="field">
            <xsl:if test="@offset|@of">
            <div class="offset">
                <xsl:value-of select="@offset|@of"/>
            </div>
            </xsl:if>
            <div class="head">
                <span class="attr type"><xsl:value-of select="@type|@ty"/></span>
                <span class="attr name"><xsl:value-of select="@name|@na"/></span>
                <span class="attr value">
                <xsl:choose>
                    <xsl:when test="@valuefmt|@vf"><xsl:value-of select="@valuefmt|@vf"/></xsl:when>
                    <xsl:otherwise><xsl:value-of select="@value|@va"/></xsl:otherwise>
                </xsl:choose>
                </span>
                <!--clickable links need text nodes, but not anchors-->
                <xsl:if test="(@type='tid' or @ty='tid')and (@value!=0 or @va!=0) and (@value!=-1 or @va!=-1)"><a class="target" href="#{@value|@va}">target</a></xsl:if>
                <xsl:if test="@type='sid' or @ty='sid'"><a class="anchor" id="{@value|@va}" href="#{@value|@va}">anchor</a></xsl:if>

                <xsl:if test="@hashname|@hn">
                    <span class="attr hashname">(<xsl:value-of select="@hashname|@hn"/>)</span>
                </xsl:if>
                <xsl:if test="@guidname|@gn">
                    <span class="attr guidname">{<xsl:value-of select="@guidname|@gn"/>}</span>
                </xsl:if>
                <xsl:if test="@objpath|@op">
                    <span class="tooltip objpath"><span class="attr objpath"><xsl:value-of select="@objpath|@op"/></span></span>
                </xsl:if>
                <xsl:if test="@path|@pa">
                    <span class="tooltip path"><span class="attr path"><xsl:value-of select="@path|@pa"/></span></span>
                </xsl:if>
            </div>
            <xsl:if test="*">
            <div class="body">
                <xsl:apply-templates />
            </div>
            </xsl:if>
        </div>
    </xsl:template>

    <xsl:template match="skip">
        <div class="skip">
            (skipped <xsl:value-of select="@size|@si"/>)
            <xsl:apply-templates />
        </div>
    </xsl:template>

    <xsl:template match="error">
        <div class="error">
            error: <xsl:value-of select="@message|@me"/>
            <xsl:apply-templates />
        </div>
    </xsl:template>

</xsl:stylesheet>

<!-- XML -->
<base>
