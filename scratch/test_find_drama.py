import sys, os, urllib.request, urllib.parse, json
sys.stdout.reconfigure(encoding='utf-8')

def test_cms_api(kw):
    url = f"https://www.hongguoapp.cn/api.php/provide/vod/?ac=detail&wd={urllib.parse.quote(kw)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
            print("API response ok, total:", data.get("total"))
            for list_item in data.get("list", [])[:5]:
                print("ID:", list_item.get("vod_id"), "| Name:", list_item.get("vod_name"))
    except Exception as e:
        print("API error:", e)

test_cms_api("丑小鸭")
test_cms_api("万人迷")
test_cms_api("重生")
