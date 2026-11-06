# Podcast cartoon video

`podcast_cartoon_lipsync.mp4` waa muuqaal **5 daqiiqo ah, 1672×940, 24 fps**. Sawirka cartoon-ka waxaa lagu daray dhaqaaq af ah oo 2D ah oo raaca xoogga codka iyo dhexdhexaaddiisa.

Codka MP3-ga videoga ku jira waa isla `audio/qaybo_5min/qayb_00.mp3`; dib looma encode-gareyn, loona beddelin dhererkiisa ama tayadiisa.

GitHub ka fur faylka MP4, kadib guji **Download raw file** si aad u soo dejisato.

## Dib u samee

Waxaa loo baahan yahay Python 3 iyo FFmpeg.

```sh
python3 -m pip install -r scripts/requirements.txt
python3 scripts/animate_podcast.py \
  assets/warm_podcast_studio_conversation.png \
  audio/qaybo_5min/qayb_00.mp3 \
  output/podcast_cartoon_lipsync.mp4
```

Tani waa animation 2D ah oo afka kiciya, ma aha lip-sync AI ah oo dhaqaaq dhab ah dhaliya.
