import asyncio, json, re, pathlib, tempfile, subprocess
import edge_tts

async def main():
    p=pathlib.Path('index.html')
    s=p.read_text(encoding='utf-8')
    bank=json.JSONDecoder().raw_decode(re.search(r'(?:var|const|let)\s+bank\s*=\s*',s) and s[re.search(r'(?:var|const|let)\s+bank\s*=\s*',s).end():])[0]
    questions=[q for q in bank if q.get('audio')]
    assert len(bank)==600 and len(questions)==90
    with tempfile.TemporaryDirectory() as tmp:
        root=pathlib.Path(tmp)
        for q in questions:
            parts=re.split(r'([男女][：:])',q['audio'])
            voice='zh-TW-HsiaoChenNeural'; clips=[]
            for part in parts:
                if re.fullmatch(r'[男女][：:]',part):
                    voice='zh-TW-YunJheNeural' if part[0]=='男' else 'zh-TW-HsiaoChenNeural'; continue
                if not part.strip(): continue
                clip=root/f'{q["id"]}-{len(clips)}.mp3'
                for attempt in range(3):
                    try:
                        await edge_tts.Communicate(part.strip(),voice,rate='-10%').save(str(clip)); break
                    except Exception:
                        if attempt==2: raise
                        await asyncio.sleep(3*(attempt+1))
                clips.append(clip)
            args=['ffmpeg','-v','error','-y']
            for clip in clips: args+=['-i',str(clip)]
            filters=';'.join(f'[{i}:a]aresample=24000,aformat=channel_layouts=mono,apad=pad_dur=0.35[a{i}]' for i in range(len(clips)))+';'+''.join(f'[a{i}]' for i in range(len(clips)))+f'concat=n={len(clips)}:v=0:a=1[out]'
            dest=root/f'{q["id"]}.mp3'
            subprocess.run(args+['-filter_complex',filters,'-map','[out]','-codec:a','libmp3lame','-b:a','64k',str(dest)],check=True)
            subprocess.run(['ffmpeg','-v','error','-i',str(dest),'-f','null','-'],check=True)
            print(q['id'],flush=True)
        pathlib.Path('audio').mkdir(exist_ok=True)
        for q in questions: (pathlib.Path('audio')/f'{q["id"]}.mp3').write_bytes((root/f'{q["id"]}.mp3').read_bytes())
    s=s.replace('3.3','3.4')
    start=s.index('function addAudio(q) {')
    end=s.index('if (window.speechSynthesis)\n    window.speechSynthesis.getVoices();',start)
    s=s[:start]+"""function addAudio(q) {
    var player=document.createElement('audio');
    player.controls=true; player.preload='none'; player.style.width='100%';
    player.src='audio/'+q.id+'.mp3?v=34';
    app.appendChild(player);
    player.onplay=function(){if(activeAudio && activeAudio!==player) activeAudio.pause(); activeAudio=player;};
    btn('audio',t(19),function(){stopAudio(); activeAudio=player; player.currentTime=0; var p=player.play(); if(p && p.catch) p.catch(function(){status.textContent=t(25);});});
    var status=document.createElement('small'); app.appendChild(status);
    player.onerror=function(){status.textContent=t(25);};
}
"""+s[end:]
    p.write_text(s,encoding='utf-8')
asyncio.run(main())
