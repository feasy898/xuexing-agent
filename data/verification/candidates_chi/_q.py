import subprocess, re, html, urllib.parse, sys

q = sys.argv[1]
key = sys.argv[2] if len(sys.argv) > 2 else None
eng = sys.argv[3] if len(sys.argv) > 3 else 'sm'
urls = {
    'sm': 'https://so.m.sm.cn/s?q=',
    'bd': 'https://www.baidu.com/s?wd=',
    'sg': 'https://www.sogou.com/web?query=',
    'bing': 'https://cn.bing.com/search?q=',
}
url = urls[eng] + urllib.parse.quote(q)
out = subprocess.run(
    ['curl', '-sL', '-m', '25', '-A',
     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120', url],
    capture_output=True).stdout.decode('utf-8', 'ignore')
print('len', len(out))
b = re.sub(r'<(script|style).*?</\1>', '', out, flags=re.S)
x = html.unescape(re.sub(r'<[^>]+>', '\n', b))
x = re.sub(r'\n\s*\n+', '\n', x)
if key:
    idx = [m.start() for m in re.finditer(key, x)]
    print('hits', len(idx))
    for i in idx[:3]:
        print('---')
        print(x[max(0, i - 200):i + 1500])
else:
    print(x[:2500])
