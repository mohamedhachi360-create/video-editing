import csv, json, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
meta=json.load(open("img/meta.json"))
qs=[]
for r in csv.reader(open("scenes.tsv"),delimiter="\t"):
    if r and not r[0].startswith("#") and not r[1].startswith("@") and r[1] not in qs: qs.append(r[1])
if len(sys.argv)>1: qs=[q for q in qs if q in sys.argv[1:]]
W,H,C=320,180,6
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
per=C*7
for s in range(0,len(qs),per):
    chunk=qs[s:s+per]; rows=(len(chunk)+C-1)//C
    sh=Image.new("RGB",(C*W,rows*(H+22)),"white"); d=ImageDraw.Draw(sh)
    for i,q in enumerate(chunk):
        x,y=(i%C)*W,(i//C)*(H+22)
        if q in meta: sh.paste(ImageOps.fit(Image.open(meta[q]["path"]).convert("RGB"),(W,H)),(x,y+22))
        d.text((x+4,y+2),f"{s+i}:{q}"[:32],fill="black",font=font)
    sh.save(f"sheet_{s//per}.jpg",quality=80); print(f"sheet_{s//per}.jpg")
