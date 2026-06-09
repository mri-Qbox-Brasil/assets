#!/usr/bin/env python3
"""Scraper de blips e markers do FiveM.

Baixa as imagens de referencia de blips e markers da documentacao oficial do
FiveM e salva cada arquivo nomeado como ``{id}_{nome}.{ext}`` (id com
zero-padding). Gera tambem um index.json com o mapeamento id <-> nome <->
arquivo.

Fonte dos dados: arquivos markdown oficiais do repo citizenfx/fivem-docs
(content/docs/game-references/{blips,markers}.md). As imagens vem de
docs.fivem.net. A extensao de cada blip vem do proprio source (alguns sao
.gif animados, a maioria .png) -- nunca assumida.

Uso:
    python scrape_fivem_refs.py                 # baixa tudo para ./blips e ./markers
    python scrape_fivem_refs.py --dry-run       # so faz o parse e escreve o index
    python scrape_fivem_refs.py --only markers  # so markers
    python scrape_fivem_refs.py --output dest   # outra pasta de saida
"""

import os
import re
import json
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

RAW_BASE = (
    "https://raw.githubusercontent.com/citizenfx/fivem-docs/"
    "{ref}/content/docs/game-references/{page}.md"
)
IMG_BASE = "https://docs.fivem.net"
USER_AGENT = "mri-assets-fivem-scraper/1.0 (+https://docs.fivem.net)"

# Cada entrada e uma unica linha no markdown. Capturamos o src da imagem,
# o id (dentro de <strong>) e o nome. Sem DOTALL de proposito: assim o "."
# nao atravessa linhas / entradas vizinhas.
ENTRY_RE = re.compile(
    r'<img src="(?P<src>{prefix}[^"]+)"[^>]*>.*?'
    r'<strong>(?P<id>\d+)</strong><br>(?P<name>[^<]*)</span>'
)


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def safe_name(name):
    """Sanitiza o nome para uso em filename (Windows-safe)."""
    name = (name or "").strip()
    if not name or name == "?":
        return "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def parse_entries(md_text, prefix):
    """Extrai (id, nome, src, ext) de um markdown de referencia do FiveM.

    Pula a linha de template (que contem ``${``) e deduplica por id mantendo
    a primeira ocorrencia.
    """
    pat = re.compile(ENTRY_RE.pattern.format(prefix=re.escape(prefix)))
    entries = {}
    for line in md_text.splitlines():
        if "${" in line:  # linha de template/comentario, nao e dado real
            continue
        m = pat.search(line)
        if not m:
            continue
        _id = int(m.group("id"))
        if _id in entries:
            continue
        src = m.group("src")
        _, ext = os.path.splitext(src)
        entries[_id] = {
            "id": _id,
            "name": m.group("name").strip(),
            "src": src,
            "ext": ext.lower(),
        }
    return [entries[k] for k in sorted(entries)]


def build_records(entries, subdir):
    """Adiciona filename ({id}_{nome}.ext, id zero-padded) e url a cada entry."""
    if not entries:
        return []
    pad = len(str(max(e["id"] for e in entries)))
    records = []
    for e in entries:
        fname = f"{e['id']:0{pad}d}_{safe_name(e['name'])}{e['ext']}"
        records.append({
            **e,
            "file": f"{subdir}/{fname}",
            "url": IMG_BASE + e["src"],
        })
    return records


def download(url, dest, retries=3):
    """Baixa url -> dest. Pula se ja existir e nao estiver vazio (resume)."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "skip"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if not data:
                raise ValueError("resposta vazia")
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dest)
            return "ok"
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.5 * (attempt + 1))
    return f"erro: {last_err}"


def download_all(records, base_dir, workers):
    results = {"ok": 0, "skip": 0, "erro": 0}
    errors = []

    def task(rec):
        dest = os.path.join(base_dir, rec["file"].replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        return rec, download(rec["url"], dest)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(task, r) for r in records]
        done = 0
        total = len(records)
        for fut in as_completed(futures):
            rec, status = fut.result()
            done += 1
            if status == "ok":
                results["ok"] += 1
            elif status == "skip":
                results["skip"] += 1
            else:
                results["erro"] += 1
                errors.append((rec["url"], status))
            if done % 100 == 0 or done == total:
                print(f"  {done}/{total} "
                      f"(ok={results['ok']} skip={results['skip']} erro={results['erro']})")
    return results, errors


def main():
    p = argparse.ArgumentParser(description="Scraper de blips/markers do FiveM.")
    p.add_argument("--output", default=".", help="Pasta base de saida")
    p.add_argument("--ref", default="master", help="Branch/tag do repo fivem-docs")
    p.add_argument("--index", default="fivem_refs_index.json", help="Arquivo de indice")
    p.add_argument("--only", choices=["blips", "markers", "both"], default="both")
    p.add_argument("--workers", type=int, default=8, help="Downloads paralelos")
    p.add_argument("--dry-run", action="store_true", help="So faz o parse + index")
    args = p.parse_args()

    pages = []
    if args.only in ("blips", "both"):
        pages.append(("blips", "/blips/"))
    if args.only in ("markers", "both"):
        pages.append(("markers", "/markers/"))

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "citizenfx/fivem-docs@" + args.ref,
        "image_base": IMG_BASE,
    }

    all_records = {}
    for page, prefix in pages:
        url = RAW_BASE.format(ref=args.ref, page=page)
        print(f"Lendo source: {url}")
        md = fetch_text(url)
        entries = parse_entries(md, prefix)
        records = build_records(entries, page)
        all_records[page] = records
        gifs = sum(1 for r in records if r["ext"] == ".gif")
        print(f"  {page}: {len(records)} entradas "
              f"(ids {records[0]['id']}..{records[-1]['id']}, "
              f"{gifs} .gif / {len(records) - gifs} outras)")

    os.makedirs(args.output, exist_ok=True)
    index_path = os.path.join(args.output, args.index)

    def write_index():
        index["pages"] = sorted(all_records)
        for page, records in all_records.items():
            index[page] = records
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"Indice escrito em: {os.path.abspath(index_path)}")

    if args.dry_run:
        write_index()
        print("--dry-run: nenhuma imagem baixada.")
        return

    index["stats"] = {}
    for page, records in all_records.items():
        print(f"Baixando {page} ({len(records)} imagens)...")
        results, errors = download_all(records, args.output, args.workers)
        # Marca disponibilidade real: arquivo existe e nao esta vazio.
        for r in records:
            dest = os.path.join(args.output, r["file"].replace("/", os.sep))
            r["available"] = os.path.exists(dest) and os.path.getsize(dest) > 0
        available = sum(1 for r in records if r["available"])
        index["stats"][page] = {
            "total": len(records),
            "available": available,
            "missing": len(records) - available,
        }
        print(f"  {page} concluido: ok={results['ok']} "
              f"skip={results['skip']} erro={results['erro']} "
              f"(disponiveis={available}/{len(records)})")
        if errors:
            missing_names = sorted({r["name"] for r in records if not r["available"]})
            print(f"  {len(missing_names)} nome(s) sem imagem no CDN do FiveM "
                  f"(marcados available=false no index): {', '.join(missing_names[:8])}"
                  f"{' ...' if len(missing_names) > 8 else ''}")

    write_index()


if __name__ == "__main__":
    main()
