#!/usr/bin/env python3
"""
Pull the HHS OCR breach data (Under Investigation + Archive) by replicating the
portal's own CSV export (a PrimeFaces/JSF form POST). No browser needed.

Recipe proven by inspecting the live portal:
  1. GET the page -> JSESSIONID cookie + javax.faces.ViewState + the CSV export link id.
  2. POST the ocrForm fields + "<csvLinkId>=<csvLinkId>" -> text/csv download.
  3. For Archive: flip the tabView to the Archive tab (activeIndex=1) via a JSF
     ajax postback, then export again.
"""
import re, sys, warnings
warnings.filterwarnings("ignore")
import requests

BASE = "https://ocrportal.hhs.gov/ocr/breach/breach_report_hip.jsf"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

def slice_form(html, form_id):
    m = re.search(r'<form[^>]*id="%s".*?</form>' % re.escape(form_id), html, re.S)
    return m.group(0) if m else html

def parse_hidden_inputs(form_html):
    fields = {}
    for m in re.finditer(r'<input[^>]*>', form_html, re.S):
        tag = m.group(0)
        name = re.search(r'name="([^"]+)"', tag)
        if not name:
            continue
        val = re.search(r'value="([^"]*)"', tag)
        fields[name.group(1)] = val.group(1) if val else ""
    # selects: take the option marked selected (rows-per-page dropdown)
    for sm in re.finditer(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', form_html, re.S):
        sname, body = sm.group(1), sm.group(2)
        opt = re.search(r'<option[^>]*value="([^"]*)"[^>]*selected', body)
        if not opt:
            opt = re.search(r'<option[^>]*value="([^"]*)"', body)
        fields[sname] = opt.group(1) if opt else ""
    return fields

def find_csv_link_id(html):
    # The CSV icon's <a> fires mojarra.jsfcljs(form,{'<id>':'<id>'},'') then wraps
    # an <img title="Export as CSV">. Pull the param key out of that onclick.
    m = re.search(r"mojarra\.jsfcljs\([^,]*,\{'([^']+)':'[^']*'\}[^>]*>\s*<img[^>]*title=\"Export as CSV\"", html, re.S)
    return m.group(1) if m else None

def export_csv(session, archive=False):
    r = session.get(BASE, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    html = r.text
    form_html = slice_form(html, "ocrForm")
    fields = parse_hidden_inputs(form_html)
    link_id = find_csv_link_id(html)
    if not link_id:
        raise RuntimeError("could not locate CSV export link id")
    tv = re.search(r'name="([^"]+)_activeIndex"', form_html)
    tabview = tv.group(1) if tv else None

    if archive and tabview:
        # PrimeFaces tabChange ajax -> activate the Archive tab (index 1)
        ajax = dict(fields)
        ajax.update({
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": tabview,
            "javax.faces.partial.execute": tabview,
            "javax.faces.partial.render": "ocrForm:breachReports ocrForm:results",
            "javax.faces.behavior.event": "tabChange",
            tabview + "_activeIndex": "1",
            tabview + "_newTab": "ocrForm:j_idt31:archiveTab",
        })
        pr = session.post(BASE, data=ajax,
                          headers={"User-Agent": UA, "Faces-Request": "partial/ajax",
                                   "X-Requested-With": "XMLHttpRequest",
                                   "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                   "Referer": BASE}, timeout=120)
        vm = re.search(r'ViewState[^>]*><!\[CDATA\[(.*?)\]\]>', pr.text, re.S)
        if vm:
            fields["javax.faces.ViewState"] = vm.group(1)
        fields[tabview + "_activeIndex"] = "1"

    fields[link_id] = link_id
    resp = session.post(BASE, data=fields,
                        headers={"User-Agent": UA,
                                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                 "Referer": BASE}, timeout=180)
    return resp, link_id

def pull(name, archive):
    s = requests.Session()
    resp, link_id = export_csv(s, archive=archive)
    ct = resp.headers.get("content-type", "")
    ok = "text/csv" in ct
    print("%-20s -> status %s | type %s | bytes %s | rows %s" % (
        name, resp.status_code, ct, len(resp.content), resp.text.count("\n") - 1))
    if ok:
        path = "data/%s.csv" % ("archive" if archive else "under_investigation")
        open(path, "w", encoding="utf-8").write(resp.text)
        print("  saved", path)
    else:
        print("  NOT CSV -- first 200:", resp.text[:200].replace("\n", " "))
    return ok

def main():
    import os
    os.makedirs("data", exist_ok=True)
    a = pull("Under Investigation", archive=False)
    b = pull("Archive", archive=True)
    sys.exit(0 if (a and b) else 1)

if __name__ == "__main__":
    main()
