"""Inject showcase/showcase_data.json into showcase/template.html -> showcase/meridian_report.html."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "showcase"


def main() -> None:
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    data = (ROOT / "showcase_data.json").read_text(encoding="utf-8")
    data = data.replace("</", "<\\/")  # never close the <script> element early
    marker = "/*__SHOWCASE_DATA__*/"
    assert template.count(marker) == 1
    out = ROOT / "meridian_report.html"
    out.write_text(template.replace(marker, data), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
