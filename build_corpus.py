"""Download TypeSafe docs pages (not SDK/legal) and split them into passages, one per ## heading."""
import json, re, pathlib, urllib.request
idx = urllib.request.urlopen("https://docs.typesafe.ai/llms.txt").read().decode()
urls = [u for u in re.findall(r"\]\((https://docs\.typesafe\.ai/[^)]+\.md)\)", idx)
        if "/sdk" not in u and "/legal" not in u and "/demos" not in u]
raw = pathlib.Path("raw"); raw.mkdir(exist_ok=True)
passages = []
for u in urls:
    slug = u.split("docs.typesafe.ai/")[1][:-3].replace("/", "__")
    f = raw / f"{slug}.md"
    if not f.exists(): f.write_text(urllib.request.urlopen(u).read().decode())
    t = f.read_text()
    t = re.sub(r"^>.*\n", "", t, flags=re.M)                       # docs index banner
    t = re.sub(r"```.*?```", "", t, flags=re.S)                   # code blocks
    t = re.sub(r"^export (?:const|function) .*?^\}[;]?\s*$", "", t, flags=re.S | re.M)  # MDX components
    t = re.sub(r"<[^>\n]+>", "", t)                                # mdx tags
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)                 # links -> text
    page = re.search(r"^# (.+)$", t, re.M); page = page.group(1).strip() if page else slug
    parts = re.split(r"^## (.+)$", t, flags=re.M)
    secs = [("Overview", parts[0])] + list(zip(parts[1::2], parts[2::2]))
    for i, (h, body) in enumerate(secs):
        body = re.sub(r"\n{3,}", "\n\n", body.replace(f"# {page}", "")).strip()
        if len(body) < 120: continue
        passages.append({"id": f"{slug}#{i}", "title": f"{page}: {h.strip()}", "text": body[:2000]})
json.dump(passages, open("corpus.json", "w"), ensure_ascii=False, indent=1)
print(len(urls), "pages", len(passages), "passages")
