// Scene view for the TAP GUI: an illustrated picture of the current room with
// clickable exits, characters and items, plus an animated combat screen.
// All artwork is original inline SVG drawn here (no external images).
// The scene only sends ordinary TAP commands through send() from ui.html.
(() => {
  'use strict';
  const byId = (id) => document.getElementById(id);
  const DIRS = ['north', 'east', 'south', 'west'];
  const OPPOSITE = { north: 'south', south: 'north', east: 'west', west: 'east' };
  const ARROW = { north: '▲', south: '▼', east: '▶', west: '◀' };
  const cat = () => (typeof catalog !== 'undefined' && catalog) || {};
  const me = () => (typeof playerName !== 'undefined' ? playerName : '');
  const act = (line) => {
    if (typeof send === 'function') return send(line);
  };
  const nameOf = (type, id) =>
    cat()[type]?.[id]?.name ||
    String(id)
      .replace(/^(item|npc|loc)\./, '')
      .replaceAll('_', ' ');
  const has = (id, ...words) => words.some((word) => String(id).toLowerCase().includes(word));

  function hash(text) {
    let hashValue = 7;
    for (const ch of String(text)) hashValue = (hashValue * 31 + ch.charCodeAt(0)) | 0;
    return Math.abs(hashValue);
  }

  function rng(seed) {
    let seedValue = seed || 1;
    return () => {
      seedValue = (seedValue * 1103515245 + 12345) & 0x7fffffff;
      return seedValue / 0x7fffffff;
    };
  }

  function el(tag, cls, text) {
    const element = document.createElement(tag);
    if (cls) element.className = cls;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function parseJSON(line) {
    try {
      return JSON.parse(line.replace(/^OK /, ''));
    } catch {
      return null;
    }
  }

  // ------------------------------------------------------------------ room art
  const svgOpen = `<svg viewBox="0 0 1000 420" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">`;

  function sky(top, bottom) {
    return `<defs>
      <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${top}"/>
      <stop offset="1" stop-color="${bottom}"/>
      </linearGradient>
      </defs>
      <rect width="1000" height="420" fill="url(#sky)"/>`;
  }

  function stars(count, seed, maxY = 200, color = '#fff') {
    const random = rng(seed);
    let markup = '';
    for (let index = 0; index < count; index++)
      markup += `<circle class="twinkle" style="animation-delay:${(random() * 3).toFixed(2)}s" cx="${(random() * 1000).toFixed(0)}" cy="${(random() * maxY).toFixed(0)}" r="${(random() * 1.6 + 0.6).toFixed(1)}" fill="${color}"/>`;
    return markup;
  }

  function flame(posX, posY, scale = 1, colors = ['#ff7a1a', '#ffd34d']) {
    return `<g transform="translate(${posX} ${posY}) scale(${scale})">
      <path class="flicker" d="M0 0 C-14 -10 -10 -30 0 -48 C10 -30 14 -10 0 0Z" fill="${colors[0]}"/>
      <path class="flicker" style="animation-delay:.2s" d="M0 0 C-7 -6 -6 -18 0 -28 C6 -18 7 -6 0 0Z" fill="${colors[1]}"/>
      </g>`;
  }

  function tree(posX, posY, scale, color) {
    return `<g transform="translate(${posX} ${posY}) scale(${scale})">
      <rect x="-7" y="-10" width="14" height="60" fill="#2b1d14"/>
      <polygon points="0,-130 -55,-30 55,-30" fill="${color}"/>
      <polygon points="0,-170 -42,-80 42,-80" fill="${color}"/>
      <polygon points="0,-200 -28,-130 28,-130" fill="${color}"/>
      </g>`;
  }

  const ART = {
    square(won) {
      let markup = sky(won ? '#ffb46b' : '#0a1330', won ? '#ffe8b8' : '#28395f');
      markup += won
        ? '<circle class="glow" cx="840" cy="95" r="52" fill="#fff4c9"/>'
        : stars(70, 3, 180);
      for (const [posX, width, height] of [
        [0, 120, 150],
        [110, 90, 120],
        [190, 110, 170],
        [700, 120, 160],
        [810, 90, 130],
        [890, 110, 180],
      ]) {
        markup += `<rect x="${posX}" y="${300 - height}" width="${width}" height="${height}" fill="${won ? '#6d5a72' : '#141d36'}"/>
          <polygon points="${posX - 6},${300 - height} ${posX + width / 2},${260 - height} ${posX + width + 6},${300 - height}" fill="${won ? '#5a4560' : '#0f162b'}"/>`;
        for (let index = 0; index < 3; index++)
          markup += `<rect class="glow" style="animation-delay:${index * 0.7 + posX / 300}s" x="${posX + 18 + index * 28}" y="${320 - height + 30}" width="12" height="16" fill="#ffd27a"/>`;
      }
      markup += `<circle class="spin" cx="440" cy="120" r="40" fill="none" stroke="#6e5a2e" stroke-width="12" stroke-dasharray="12 8"/>`;
      markup += `<rect x="430" y="55" width="140" height="250" fill="#2b3555"/>
          <polygon points="420,58 500,0 580,58" fill="#1d2440"/>`;
      markup +=
        '<circle cx="500" cy="130" r="50" fill="#f3e6c6" stroke="#b88a3c" stroke-width="7"/>';
      for (let index = 0; index < 12; index++) {
        const angle = (index * Math.PI) / 6;
        markup += `<line x1="${500 + 40 * Math.sin(angle)}" y1="${130 - 40 * Math.cos(angle)}" x2="${500 + 46 * Math.sin(angle)}" y2="${130 - 46 * Math.cos(angle)}" stroke="#5a4520" stroke-width="3"/>`;
      }
      markup += `<g class="${won ? 'spin-fast' : ''}">
        <line x1="500" y1="130" x2="500" y2="${won ? 92 : 88}" stroke="#2a1d0c" stroke-width="5" stroke-linecap="round"/>
        <line x1="500" y1="130" x2="500" y2="${won ? 168 : 100}" stroke="#2a1d0c" stroke-width="7" stroke-linecap="round"/>
        </g>
        <circle cx="500" cy="130" r="5" fill="#2a1d0c"/>`;
      markup += '<rect y="300" width="1000" height="120" fill="#3b4258"/>';
      for (let index = 0; index < 12; index++)
        markup += `<line x1="${index * 90}" y1="300" x2="${index * 90 - 60}" y2="420" stroke="#30364a" stroke-width="3"/>`;
      markup += `<ellipse cx="250" cy="318" rx="80" ry="18" fill="#5a6a8c"/>
          <ellipse cx="250" cy="314" rx="64" ry="11" fill="#7fb6e0"/>
          <rect x="243" y="262" width="14" height="52" fill="#5a6a8c"/>`;
      for (let index = 0; index < 4; index++)
        markup += `<circle class="drip" style="animation-delay:${index * 0.35}s" cx="${236 + index * 9}" cy="266" r="3" fill="#bfe6ff"/>`;
      for (const posX of [100, 900])
        markup += `<rect x="${posX - 3}" y="215" width="6" height="90" fill="#222"/>
          <circle class="glow" cx="${posX}" cy="210" r="14" fill="#ffd27a"/>`;
      return markup;
    },
    market() {
      let markup = sky('#2a1640', '#5b2e4f') + stars(30, 5, 120);
      markup += '<rect y="70" width="1000" height="240" fill="#3b2433"/>';
      for (let index = 0; index < 6; index++)
        markup += `<path d="M${index * 170 - 10} 310 V150 Q${index * 170 + 75} 70 ${index * 170 + 160} 150 V310" fill="#1d1020" stroke="#7a4a3a" stroke-width="10"/>`;
      markup += '<rect x="440" y="150" width="120" height="160" fill="#111"/>';
      for (let index = 0; index < 6; index++)
        markup += `<rect x="${448 + index * 19}" y="150" width="6" height="160" fill="#5b5f6b"/>`;
      markup += '<circle class="glow" cx="500" cy="235" r="12" fill="#c97b3a"/>';
      for (const [posX, c1, c2] of [
        [60, '#c0392b', '#f5deb3'],
        [230, '#2471a3', '#f5deb3'],
        [640, '#1e8449', '#f5deb3'],
        [810, '#b7950b', '#f5deb3'],
      ]) {
        markup += `<rect x="${posX}" y="250" width="140" height="60" fill="#6b4226"/>`;
        for (let index = 0; index < 7; index++)
          markup += `<rect x="${posX - 10 + index * 23}" y="222" width="23" height="28" fill="${index % 2 ? c1 : c2}"/>`;
        markup += `<circle cx="${posX + 35}" cy="243" r="9" fill="#e67e22"/>
          <circle cx="${posX + 70}" cy="243" r="9" fill="#d35400"/>
          <circle cx="${posX + 105}" cy="243" r="9" fill="#f1c40f"/>`;
      }
      for (let index = 0; index < 5; index++)
        markup += `<g class="sway" style="animation-delay:${index * 0.4}s">
          <line x1="${165 + index * 170}" y1="85" x2="${165 + index * 170}" y2="125" stroke="#222" stroke-width="2"/>
          <rect x="${155 + index * 170}" y="125" width="20" height="26" rx="5" fill="#ffb347"/>
          <circle class="glow" cx="${165 + index * 170}" cy="138" r="22" fill="#ffb34733"/>
          </g>`;
      markup += '<rect y="310" width="1000" height="110" fill="#4a2f2a"/>';
      return markup;
    },
    library() {
      let markup = '<rect width="1000" height="420" fill="#2c1d16"/>';
      const random = rng(11);
      for (const x0 of [30, 360, 690]) {
        markup += `<rect x="${x0}" y="30" width="280" height="290" fill="#4a2f1f" stroke="#2a1a10" stroke-width="8"/>`;
        for (let row = 0; row < 5; row++) {
          let posX = x0 + 10;
          markup += `<rect x="${x0}" y="${86 + row * 56}" width="280" height="6" fill="#2a1a10"/>`;
          while (posX < x0 + 262) {
            const width = 10 + random() * 14,
              height = 34 + random() * 14;
            markup += `<rect x="${posX.toFixed(0)}" y="${(86 + row * 56 - height).toFixed(0)}" width="${width.toFixed(0)}" height="${height.toFixed(0)}" fill="hsl(${(random() * 360).toFixed(0)} 45% 38%)"/>`;
            posX += width + 2;
          }
        }
      }
      markup += `<rect y="320" width="1000" height="100" fill="#3d2a1e"/>
          <rect x="420" y="250" width="160" height="70" fill="#5a3a24"/>`;
      markup += `<g class="bobbing">
          <rect x="470" y="160" width="60" height="44" rx="4" fill="#d8c79e" transform="rotate(-8 500 182)"/>
          <line x1="500" y1="158" x2="500" y2="206" stroke="#8b6b3e" stroke-width="3"/>
          <circle class="glow" cx="500" cy="182" r="46" fill="#ffe9a822"/>
          </g>`;
      for (const posX of [440, 560])
        markup += `<rect x="${posX - 5}" y="226" width="10" height="24" fill="#f3ead2"/>${flame(posX, 228, 0.45)}`;
      markup += stars(26, 8, 300, '#ffe9a8');
      return markup;
    },
    garden() {
      let markup = sky('#05261f', '#0d3b33');
      for (let index = 0; index < 7; index++)
        markup += `<path d="M${-100 + index * 200} 320 Q${index * 200} -60 ${100 + index * 200} 320" fill="none" stroke="#9ff3e855" stroke-width="3"/>`;
      markup +=
        '<path d="M0 60 Q500 -60 1000 60" fill="none" stroke="#9ff3e877" stroke-width="5"/>';
      for (let index = 0; index < 9; index++)
        markup += `<path class="glow" style="animation-delay:${index * 0.3}s" d="M${40 + index * 115} 310 C${10 + index * 115} 240 ${80 + index * 115} 200 ${50 + index * 115} 120" fill="none" stroke="#5dffb0" stroke-width="5" stroke-linecap="round"/>`;
      markup += '<rect y="300" width="1000" height="120" fill="#123326"/>';
      for (let index = 0; index < 14; index++)
        markup += `<ellipse cx="${30 + index * 72}" cy="304" rx="30" ry="14" fill="#1f6b45"/>`;
      const random = rng(21);
      for (let index = 0; index < 22; index++)
        markup += `<circle class="fly" style="animation-delay:${(random() * 5).toFixed(1)}s;animation-duration:${(4 + random() * 4).toFixed(1)}s" cx="${(random() * 1000).toFixed(0)}" cy="${(80 + random() * 200).toFixed(0)}" r="3" fill="#eaff7a"/>`;
      return markup;
    },
    tower() {
      let markup = '<rect width="1000" height="420" fill="#2d3038"/>';
      for (let posY = 0; posY < 320; posY += 40)
        for (let posX = (posY / 40) % 2 ? -40 : 0; posX < 1000; posX += 80)
          markup += `<rect x="${posX}" y="${posY}" width="78" height="38" fill="#363a44"/>`;
      markup +=
        '<path d="M330 300 V120 Q500 -10 670 120 V300 Z" fill="#0b1430"/>' +
        `<g>${stars(30, 9, 200)}</g>`;
      markup += `<path d="M330 300 V120 Q500 -10 670 120 V300 Z" fill="none" stroke="#1d2027" stroke-width="16"/>
          <rect x="340" y="250" width="320" height="50" fill="#0f2a1e"/>`;
      markup += `<g transform="rotate(-25 230 230)">
          <rect x="150" y="215" width="170" height="26" rx="8" fill="#9a7b4f"/>
          <rect x="300" y="210" width="26" height="36" rx="4" fill="#c6a46a"/>
          </g>
          <line x1="230" y1="235" x2="190" y2="320" stroke="#5a4630" stroke-width="7"/>
          <line x1="230" y1="235" x2="270" y2="320" stroke="#5a4630" stroke-width="7"/>`;
      for (let index = 0; index < 6; index++)
        markup += `<rect x="${760 + index * 36}" y="${300 - index * 30}" width="240" height="30" fill="#4a4f5c"/>`;
      markup += '<rect x="96" y="120" width="10" height="40" fill="#333"/>' + flame(101, 122, 0.7);
      markup += '<rect y="300" width="1000" height="120" fill="#262930"/>';
      return markup;
    },
    forest() {
      let markup = sky('#04120c', '#0f2a1d');
      const random = rng(31);
      for (let index = 0; index < 9; index++)
        markup += tree(index * 125 + 30, 300, 1.1 + random() * 0.4, '#0b2416');
      for (let index = 0; index < 4; index++)
        markup += `<g class="blink" style="animation-delay:${index * 1.1}s">
          <circle cx="${150 + index * 230}" cy="${200 + (index % 2) * 40}" r="4" fill="#ffe14d"/>
          <circle cx="${164 + index * 230}" cy="${200 + (index % 2) * 40}" r="4" fill="#ffe14d"/>
          </g>`;
      for (let index = 0; index < 7; index++)
        markup += tree(index * 160 - 40, 330, 1.5 + random() * 0.3, '#123b24');
      markup += '<rect y="318" width="1000" height="102" fill="#1a2f1c"/>';
      for (let index = 0; index < 10; index++)
        markup += `<ellipse class="fall" style="animation-delay:${(random() * 7).toFixed(1)}s" cx="${(100 + random() * 900).toFixed(0)}" cy="20" rx="7" ry="4" fill="${random() > 0.5 ? '#c96a1b' : '#e3a92d'}"/>`;
      return markup;
    },
    marsh() {
      let markup = sky('#0d1d14', '#2c4630');
      markup += '<circle cx="760" cy="80" r="40" fill="#cfe8b0" opacity=".5"/>';
      markup += `<rect y="240" width="1000" height="180" fill="#10241a"/>
          <ellipse cx="500" cy="330" rx="430" ry="70" fill="#081a12"/>`;
      for (let index = 0; index < 4; index++)
        markup += `<ellipse class="ripple" style="animation-delay:${index * 0.8}s" cx="${300 + index * 140}" cy="${320 + (index % 2) * 20}" rx="50" ry="10" fill="none" stroke="#5f8f6a" stroke-width="2"/>`;
      const random = rng(41);
      for (let index = 0; index < 40; index++) {
        const posX = random() * 1000,
          height = 40 + random() * 70;
        markup += `<line x1="${posX.toFixed(0)}" y1="${(300 + random() * 40).toFixed(0)}" x2="${(posX + random() * 16 - 8).toFixed(0)}" y2="${(300 - height).toFixed(0)}" stroke="#3e5c2f" stroke-width="3"/>`;
      }
      for (let index = 0; index < 5; index++)
        markup += `<ellipse class="drift" style="animation-delay:${index * 2}s" cx="${100 + index * 200}" cy="${230 + (index % 2) * 40}" rx="180" ry="26" fill="#a7f0b8" opacity=".14"/>`;
      return markup;
    },
    harbor() {
      let markup = sky('#071026', '#1b2c55') + stars(50, 13, 160);
      markup += '<circle class="glow" cx="180" cy="80" r="38" fill="#f4f1d0"/>';
      markup += '<rect y="230" width="1000" height="190" fill="#0a1a33"/>';
      for (let index = 0; index < 5; index++)
        markup += `<path class="wave" style="animation-delay:${index * 0.5}s" d="M-40 ${250 + index * 28} q30 -10 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0" fill="none" stroke="#2f5a8f" stroke-width="3"/>`;
      for (const [posX, delay] of [
        [620, 0],
        [800, 1.2],
      ])
        markup += `<g class="bobbing" style="animation-delay:${delay}s">
          <path d="M${posX} 250 h120 l-20 30 h-80 z" fill="#5a3b24"/>
          <line x1="${posX + 60}" y1="250" x2="${posX + 60}" y2="170" stroke="#3a2a1a" stroke-width="5"/>
          <path d="M${posX + 62} 175 l40 55 h-40 z" fill="#d8d2c0"/>
          </g>`;
      markup += '<rect x="0" y="292" width="560" height="30" fill="#6b4a2c"/>';
      for (let index = 0; index < 8; index++)
        markup += `<rect x="${20 + index * 70}" y="292" width="10" height="128" fill="#4a321d"/>`;
      markup += '<rect y="322" width="560" height="98" fill="#3b2a1a"/>';
      return markup;
    },
    tavern() {
      let markup = '<rect width="1000" height="420" fill="#4a2b18"/>';
      for (let posX = 0; posX < 1000; posX += 60)
        markup += `<rect x="${posX}" y="0" width="56" height="300" fill="#57331c"/>`;
      markup += `<rect x="380" y="110" width="240" height="190" fill="#6b6b6b"/>
          <rect x="410" y="160" width="180" height="140" fill="#1a0e08"/>`;
      markup += flame(470, 296, 1.2) + flame(510, 296, 1.5) + flame(548, 296, 1.1);
      markup += '<circle class="glow" cx="500" cy="250" r="140" fill="#ff9a3c22"/>';
      markup += `<rect x="40" y="200" width="250" height="20" fill="#3a2010"/>
          <rect x="40" y="220" width="250" height="80" fill="#5a3418"/>`;
      for (let index = 0; index < 4; index++)
        markup += `<rect x="${60 + index * 55}" y="174" width="22" height="26" rx="3" fill="#c9a24a"/>`;
      markup += `<g class="sway">
          <line x1="230" y1="60" x2="230" y2="90" stroke="#222" stroke-width="2"/>
          <circle cx="230" cy="96" r="8" fill="none" stroke="#c87533" stroke-width="4"/>
          <rect x="228" y="102" width="4" height="22" fill="#c87533"/>
          </g>`;
      markup += `<rect x="720" y="250" width="200" height="16" fill="#3a2010"/>
          <rect x="740" y="266" width="12" height="40" fill="#3a2010"/>
          <rect x="890" y="266" width="12" height="40" fill="#3a2010"/>`;
      markup += '<rect y="300" width="1000" height="120" fill="#3a2414"/>';
      return markup;
    },
    forge() {
      let markup = '<rect width="1000" height="420" fill="#16181d"/>';
      for (let posY = 0; posY < 300; posY += 36)
        for (let posX = (posY / 36) % 2 ? -30 : 0; posX < 1000; posX += 70)
          markup += `<rect x="${posX}" y="${posY}" width="68" height="34" fill="#1d2027"/>`;
      markup += `<path d="M600 300 V150 Q700 70 800 150 V300 Z" fill="#2c2f38"/>
          <path d="M640 300 V180 Q700 130 760 180 V300 Z" fill="#05070b"/>`;
      markup +=
        flame(680, 300, 1.4, ['#2f7bff', '#9fe0ff']) + flame(720, 300, 1.8, ['#2f7bff', '#9fe0ff']);
      markup += '<circle class="glow" cx="700" cy="250" r="150" fill="#3b8cff22"/>';
      for (let index = 0; index < 8; index++)
        markup += `<circle class="rise" style="animation-delay:${index * 0.22}s" cx="${670 + index * 9}" cy="230" r="2.5" fill="#bfe8ff"/>`;
      markup += `<path d="M330 270 h150 l-20 22 h-110 z" fill="#4b4f5a"/>
          <rect x="385" y="292" width="40" height="20" fill="#3a3d46"/>`;
      markup += '<rect x="80" y="150" width="140" height="150" fill="#000"/>';
      for (let index = 0; index < 6; index++)
        markup += `<rect x="${86 + index * 22}" y="150" width="6" height="150" fill="#555b66"/>`;
      markup += '<rect y="300" width="1000" height="120" fill="#22252c"/>';
      return markup;
    },
    ruins() {
      let markup = sky('#060a1e', '#1a1b3a') + stars(110, 17, 260);
      markup += `<path d="M120 90 L230 60 L300 120 L420 80" fill="none" stroke="#9fb7ff88" stroke-width="2"/>
          <path d="M640 70 L720 130 L800 90 L880 140" fill="none" stroke="#9fb7ff88" stroke-width="2"/>`;
      for (const [posX, posY] of [
        [120, 90],
        [230, 60],
        [300, 120],
        [420, 80],
        [640, 70],
        [720, 130],
        [800, 90],
        [880, 140],
      ])
        markup += `<circle class="twinkle" cx="${posX}" cy="${posY}" r="5" fill="#dfe8ff"/>`;
      for (const [posX, height] of [
        [80, 200],
        [200, 130],
        [760, 170],
        [880, 220],
      ])
        markup += `<path d="M${posX} 300 V${300 - height} l12 -14 l14 18 l12 -10 l12 8 V300 Z" fill="#5d5a66"/>`;
      markup += `<path d="M410 300 V160 Q500 70 590 160 V300 Z" fill="#3a3744" stroke="#24222b" stroke-width="10"/>`;
      markup += `<circle class="glow" cx="500" cy="170" r="20" fill="#9fd0ff"/>
          <circle cx="500" cy="170" r="12" fill="#0b0d1a"/>`;
      markup += '<rect y="300" width="1000" height="120" fill="#2a2833"/>';
      for (let index = 0; index < 6; index++)
        markup += `<rect x="${100 + index * 150}" y="${320 + (index % 3) * 20}" width="40" height="16" fill="#3c3946" transform="rotate(${index * 13} ${120 + index * 150} 330)"/>`;
      return markup;
    },
    sanctum() {
      let markup = `<defs>
          <radialGradient id="heartglow">
          <stop offset="0" stop-color="#ff6b8b"/>
          <stop offset="1" stop-color="#ff6b8b00"/>
          </radialGradient>
          </defs>`;
      markup += '<rect width="1000" height="420" fill="#0c0616"/>';
      for (let index = 0; index < 9; index++)
        markup += `<path d="M500 -40 L${index * 125} 300" stroke="#6e4ab655" stroke-width="2"/>`;
      markup +=
        '<path d="M60 300 Q500 -120 940 300" fill="none" stroke="#9b6dff66" stroke-width="5"/>';
      const random = rng(23);
      for (let index = 0; index < 12; index++) {
        const posX = (random() * 1000).toFixed(0),
          posY = (40 + random() * 200).toFixed(0);
        markup += `<polygon class="bobbing" style="animation-delay:${(random() * 3).toFixed(1)}s" points="${posX},${posY} ${+posX + 14},${+posY + 30} ${+posX - 8},${+posY + 22}" fill="#2b1d4a" stroke="#b48cff" stroke-width="1.5"/>`;
      }
      markup += '<circle class="glow" cx="500" cy="220" r="110" fill="url(#heartglow)"/>';
      markup += `<rect x="440" y="250" width="120" height="50" fill="#1d1230" stroke="#9b6dff" stroke-width="3"/>`;
      markup +=
        '<rect y="300" width="1000" height="120" fill="#120a20"/>' + stars(30, 29, 280, '#c9a2ff');
      return markup;
    },
  };

  function roomArt(id, won) {
    const key =
      Object.keys(ART).find((artKey) => has(id, artKey)) ||
      (has(id, 'observatory') ? 'ruins' : null);
    if (key) return svgOpen + ART[key](won) + '</svg>';
    const hue = hash(id) % 360; // unknown room (another team's world): generic landscape
    return (
      svgOpen +
      sky(`hsl(${hue} 40% 12%)`, `hsl(${hue} 35% 28%)`) +
      stars(40, hash(id), 160) +
      `<path d="M0 300 Q200 180 420 280 T1000 250 V420 H0Z" fill="hsl(${hue} 30% 18%)"/>
        <rect y="320" width="1000" height="100" fill="hsl(${hue} 25% 14%)"/>
        </svg>`
    );
  }

  // ------------------------------------------------------------------ sprites
  const shadow = '<ellipse cx="60" cy="155" rx="36" ry="6" fill="#0007"/>';

  function humanoid(options) {
    const coat = options.coat || '#3d5a80',
      skin = options.skin || '#f1c9a5';
    let markup = `<g opacity="${options.ghost ? 0.78 : 1}">` + shadow;
    if (options.cape)
      markup += `<path d="M40 72 Q60 64 80 72 L92 140 L28 140 Z" fill="${options.cape}"/>`;
    markup += `<rect x="46" y="118" width="11" height="34" rx="4" fill="${options.legs || '#2b2f3a'}"/>
      <rect x="63" y="118" width="11" height="34" rx="4" fill="${options.legs || '#2b2f3a'}"/>`;
    markup += `<path d="M38 72 Q60 60 82 72 L88 126 L32 126 Z" fill="${coat}"/>`;
    if (options.apron) markup += '<path d="M46 86 h28 v40 h-28z" fill="#eee5d0"/>';
    markup += `<rect x="24" y="76" width="12" height="40" rx="6" fill="${coat}" transform="rotate(12 30 76)"/>
      <rect x="84" y="76" width="12" height="40" rx="6" fill="${coat}" transform="rotate(-12 90 76)"/>`;
    markup += `<circle cx="60" cy="48" r="20" fill="${skin}"/>`;
    markup += `<g class="blink">
      <circle cx="53" cy="48" r="2.6" fill="${options.eyes || '#222'}"/>
      <circle cx="67" cy="48" r="2.6" fill="${options.eyes || '#222'}"/>
      </g>`;
    if (options.mask)
      markup += `<rect x="40" y="52" width="40" height="12" fill="${options.mask}"/>`;
    else markup += '<path d="M54 57 Q60 61 66 57" stroke="#7a4a3a" stroke-width="2" fill="none"/>';
    const hat = options.hat;
    if (hat === 'hood')
      markup += `<path d="M36 52 Q36 20 60 20 Q84 20 84 52 L80 44 Q60 30 40 44 Z" fill="${options.hatColor}"/>`;
    if (hat === 'helmet')
      markup += `<path d="M38 44 Q38 22 60 22 Q82 22 82 44 Z" fill="#9aa4b2"/>
        <rect x="58" y="10" width="4" height="14" fill="#c0392b"/>`;
    if (hat === 'cap')
      markup += `<path d="M40 38 Q60 18 80 38 Z" fill="${options.hatColor}"/>
        <rect x="36" y="36" width="48" height="5" rx="2" fill="${options.hatColor}"/>`;
    if (hat === 'turban')
      markup += `<ellipse cx="60" cy="32" rx="24" ry="13" fill="${options.hatColor}"/>
        <circle cx="60" cy="30" r="4" fill="#c0392b"/>`;
    if (hat === 'glasses')
      markup += `<g fill="none" stroke="#333" stroke-width="2">
          <circle cx="53" cy="48" r="6"/>
          <circle cx="67" cy="48" r="6"/>
          <line x1="59" y1="48" x2="61" y2="48"/>
          </g>
          <path d="M40 36 Q60 22 80 36" stroke="#ddd" stroke-width="6" fill="none"/>`;
    if (options.hair)
      markup += `<path d="M40 40 Q60 22 80 40 Q70 32 60 32 Q50 32 40 40Z" fill="${options.hair}"/>`;
    markup += options.extra || '';
    return markup + '</g>';
  }

  // Cute animal characters (cats and rabbits) for players and friendly NPCs.
  const FUR = {
    cat: ['#f0a35e', '#b9bcc6', '#f4e1c1', '#4a4a56', '#e8c49a'],
    rabbit: ['#f5f2ee', '#c8a27c', '#a9a9b3', '#e9d6c0', '#8f7a6b'],
  };

  function critter(options) {
    const species = options.species || 'cat',
      fur = options.fur || FUR[species][0],
      coat = options.coat || '#3d5a80';
    const light = options.belly || '#fff8ee',
      pink = '#f7a8b8',
      eye = '#2a1f2e';
    let markup = `<g opacity="${options.ghost ? 0.8 : 1}">` + shadow;
    // tail and cape behind the body
    if (species === 'cat')
      markup += `<path class="tail" d="M78 132 Q112 128 104 96 Q100 84 108 78" fill="none" stroke="${fur}" stroke-width="9" stroke-linecap="round"/>`;
    if (options.cape)
      markup += `<path d="M40 96 Q60 88 80 96 L92 146 L28 146 Z" fill="${options.cape}"/>`;
    if (species === 'rabbit') markup += `<circle cx="84" cy="136" r="9" fill="${light}"/>`;
    // feet, body (clothes), paws
    markup += `<ellipse cx="48" cy="150" rx="11" ry="7" fill="${fur}"/>
      <ellipse cx="72" cy="150" rx="11" ry="7" fill="${fur}"/>`;
    markup += `<path d="M36 112 Q36 90 60 90 Q84 90 84 112 L86 144 Q60 152 34 144 Z" fill="${coat}"/>`;
    if (options.apron) markup += '<path d="M46 104 h28 v38 q-14 5 -28 0z" fill="#eee5d0"/>';
    markup += `<ellipse cx="34" cy="118" rx="8" ry="10" fill="${fur}"/>
      <ellipse cx="86" cy="118" rx="8" ry="10" fill="${fur}"/>`;
    // ears
    if (species === 'cat') {
      markup += `<path d="M36 46 L32 12 L58 34 Z" fill="${fur}"/>
        <path d="M40 40 L38 20 L52 33 Z" fill="${pink}"/>`;
      markup += `<path d="M84 46 L88 12 L62 34 Z" fill="${fur}"/>
        <path d="M80 40 L82 20 L68 33 Z" fill="${pink}"/>`;
    } else {
      const flop = options.flop ? 'rotate(38 76 30)' : 'rotate(10 74 30)';
      markup += `<ellipse cx="46" cy="16" rx="10" ry="24" fill="${fur}" transform="rotate(-10 46 30)"/>
        <ellipse cx="46" cy="17" rx="5" ry="17" fill="${pink}" transform="rotate(-10 46 30)"/>`;
      markup += `<ellipse cx="74" cy="16" rx="10" ry="24" fill="${fur}" transform="${flop}"/>
        <ellipse cx="74" cy="17" rx="5" ry="17" fill="${pink}" transform="${flop}"/>`;
    }
    // head
    markup += `<circle cx="60" cy="60" r="29" fill="${fur}"/>`;
    if (options.patch)
      markup += `<path d="M40 44 Q50 34 60 40 Q56 52 44 54 Z" fill="${options.patch}"/>`;
    markup += `<ellipse cx="60" cy="72" rx="15" ry="11" fill="${light}"/>`;
    // hats that sit on the head
    const hat = options.hat;
    if (hat === 'hood')
      markup += `<path d="M28 66 Q26 26 60 26 Q94 26 92 66 L86 54 Q60 38 34 54 Z" fill="${options.hatColor}"/>`;
    if (hat === 'helmet')
      markup += `<path d="M33 48 Q33 26 60 26 Q87 26 87 48 Z" fill="#9aa4b2"/>
        <rect x="58" y="12" width="4" height="16" fill="#c0392b"/>`;
    if (hat === 'cap')
      markup += `<path d="M36 40 Q60 16 84 40 Z" fill="${options.hatColor}"/>
        <rect x="32" y="38" width="56" height="6" rx="3" fill="${options.hatColor}"/>`;
    if (hat === 'turban')
      markup += `<ellipse cx="60" cy="36" rx="27" ry="13" fill="${options.hatColor}"/>
        <circle cx="60" cy="34" r="4" fill="#c0392b"/>`;
    // face: big shiny eyes, blush, nose, mouth, whiskers
    markup += `<g class="blink">
      <ellipse cx="49" cy="60" rx="5" ry="6.5" fill="${eye}"/>
      <ellipse cx="71" cy="60" rx="5" ry="6.5" fill="${eye}"/>
      <circle cx="51" cy="57.5" r="2" fill="#fff"/>
      <circle cx="73" cy="57.5" r="2" fill="#fff"/>
      </g>`;
    markup += `<ellipse cx="40" cy="70" rx="5" ry="3" fill="${pink}" opacity=".6"/>
      <ellipse cx="80" cy="70" rx="5" ry="3" fill="${pink}" opacity=".6"/>`;
    markup +=
      species === 'cat'
        ? `<path d="M56 66 h8 l-4 4z" fill="${pink}"/>`
        : `<ellipse cx="60" cy="67" rx="3.5" ry="2.5" fill="${pink}"/>`;
    markup += `<path d="M54 72 Q57 76 60 72 Q63 76 66 72" stroke="#6b4a4a" stroke-width="1.6" fill="none" stroke-linecap="round"/>`;
    if (species === 'rabbit')
      markup += '<rect x="57.5" y="73" width="5" height="5" rx="1" fill="#fff"/>';
    if (species === 'cat')
      markup += `<g stroke="#6b5a55" stroke-width="1.2" opacity=".7">
          <line x1="44" y1="70" x2="26" y2="66"/>
          <line x1="44" y1="73" x2="26" y2="75"/>
          <line x1="76" y1="70" x2="94" y2="66"/>
          <line x1="76" y1="73" x2="94" y2="75"/>
          </g>`;
    if (hat === 'glasses')
      markup += `<g fill="none" stroke="#333" stroke-width="2">
          <circle cx="49" cy="60" r="9"/>
          <circle cx="71" cy="60" r="9"/>
          <line x1="58" y1="60" x2="62" y2="60"/>
          </g>`;
    markup += options.extra || '';
    return markup + '</g>';
  }

  const HELD = {
    scroll: `<rect x="88" y="92" width="14" height="34" rx="6" fill="#efe2bf" stroke="#b39b62" stroke-width="2"/>`,
    spear: `<line x1="98" y1="20" x2="98" y2="150" stroke="#6b4a2c" stroke-width="4"/>
        <polygon points="98,8 92,24 104,24" fill="#c0c7d0"/>`,
    sack: '<ellipse cx="96" cy="118" rx="13" ry="15" fill="#a87c4f"/>',
    book: '<rect x="86" y="100" width="20" height="24" fill="#7b2d26"/>',
    bow: `<path d="M100 60 Q122 100 100 140" fill="none" stroke="#6b4a2c" stroke-width="4"/>
      <line x1="100" y1="60" x2="100" y2="140" stroke="#ddd" stroke-width="1"/>`,
    mug: '<rect x="88" y="104" width="16" height="18" rx="2" fill="#c9a24a"/>',
    hammer: `<rect x="96" y="70" width="5" height="56" fill="#6b4a2c"/>
        <rect x="86" y="62" width="26" height="14" rx="2" fill="#9fd0ff"/>`,
    sword: `<rect x="96" y="40" width="6" height="66" fill="#d7dde6"/>
        <rect x="88" y="104" width="22" height="5" fill="#8a6b2f"/>
        <rect x="96" y="108" width="6" height="14" fill="#4a321d"/>`,
    dagger: `<rect x="96" y="92" width="5" height="26" fill="#d7dde6"/>
        <rect x="91" y="116" width="15" height="4" fill="#3a2a1a"/>
        <circle class="glow" cx="38" cy="112" r="6" fill="#9fd0ff"/>`,
  };

  function npcSprite(id) {
    const role = cat().npcs?.[id]?.role || '';
    const svg = (inner) =>
      `<svg viewBox="0 -10 120 172" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
    if (has(id, 'wolf'))
      return svg(
        `<ellipse cx="60" cy="152" rx="46" ry="6" fill="#0007"/>
          <g>
          <path d="M20 120 Q60 80 100 110 L104 128 L16 128 Z" fill="#1c1f2e"/>
          <rect x="26" y="122" width="9" height="30" fill="#151826"/>
          <rect x="44" y="124" width="9" height="28" fill="#151826"/>
          <rect x="74" y="124" width="9" height="28" fill="#151826"/>
          <rect x="90" y="122" width="9" height="30" fill="#151826"/>
          <path d="M18 118 Q2 100 8 84" stroke="#1c1f2e" stroke-width="10" fill="none" stroke-linecap="round"/>
          <path d="M84 112 Q98 80 116 92 L120 104 L100 118 Z" fill="#1c1f2e"/>
          <polygon points="96,90 100,72 106,88" fill="#1c1f2e"/>
          <polygon points="106,92 112,74 116,92" fill="#1c1f2e"/>
          <g class="blink">
          <circle cx="108" cy="98" r="3.5" fill="#ffe14d"/>
          </g>
          <path d="M112 108 l6 4 l-8 2z" fill="#eee"/>
          </g>`,
      );
    if (has(id, 'wraith', 'ghost'))
      return svg(
        `<g class="glow">
          <circle cx="60" cy="70" r="56" fill="#9fffd022"/>
          </g>
          <path d="M22 150 Q14 70 60 26 Q106 70 98 150 Q88 138 80 150 Q70 136 60 150 Q50 136 40 150 Q30 138 22 150Z" fill="#c8f0e0" opacity=".82"/>
          <g class="blink">
          <ellipse cx="48" cy="72" rx="7" ry="10" fill="#0d2a1f"/>
          <ellipse cx="72" cy="72" rx="7" ry="10" fill="#0d2a1f"/>
          </g>
          <ellipse cx="60" cy="100" rx="8" ry="12" fill="#0d2a1f"/>`,
      );
    if (has(id, 'drowned', 'sailor'))
      return svg(
        humanoid({
          coat: '#2c6e6a',
          skin: '#9fc7c0',
          eyes: '#e8fffb',
          hat: 'cap',
          hatColor: '#1f3f4f',
          extra: `<path d="M40 80 q4 20 -2 40 M78 84 q-6 18 2 38" stroke="#3f8f4a" stroke-width="4" fill="none"/>
              <circle class="drip" cx="44" cy="126" r="3" fill="#7fd3ff"/>
              <circle class="drip" style="animation-delay:.6s" cx="74" cy="128" r="3" fill="#7fd3ff"/>`,
        }),
      );
    if (has(id, 'bandit', 'thief'))
      return svg(
        humanoid({
          coat: '#7a1f2b',
          hat: 'hood',
          hatColor: '#4a0f18',
          mask: '#1a0a0e',
          extra: HELD.dagger,
        }),
      );
    if (has(id, 'warden', 'boss'))
      return svg(
        `<ellipse cx="60" cy="156" rx="48" ry="7" fill="#0009"/>
          <g class="glow">
          <circle cx="60" cy="80" r="70" fill="#9b6dff22"/>
          </g>
          <path d="M28 152 L36 96 L84 96 L92 152 Z" fill="#1a1428" stroke="#9b6dff" stroke-width="2"/>
          <path d="M22 60 L60 44 L98 60 L92 110 L28 110 Z" fill="#241a38" stroke="#b48cff" stroke-width="2"/>
          <circle class="glow" cx="60" cy="80" r="10" fill="#ff6b8b"/>
          <path d="M40 44 L44 8 L60 0 L76 8 L80 44 Z" fill="#1a1428" stroke="#b48cff" stroke-width="2"/>
          <g class="blink">
          <rect x="48" y="22" width="9" height="4" fill="#e3c9ff"/>
          <rect x="64" y="22" width="9" height="4" fill="#e3c9ff"/>
          </g>
          <rect x="100" y="0" width="7" height="120" fill="#b48cff"/>
          <rect x="92" y="112" width="23" height="6" fill="#4a3a6b"/>`,
      );
    if (role === 'enemy')
      return svg(
        `<ellipse cx="60" cy="152" rx="42" ry="6" fill="#0007"/>
          <path d="M20 150 Q10 70 60 50 Q110 70 100 150 Z" fill="hsl(${hash(id) % 360} 45% 32%)"/>
          <g class="blink">
          <circle cx="46" cy="96" r="8" fill="#fff"/>
          <circle cx="74" cy="96" r="8" fill="#fff"/>
          <circle cx="46" cy="98" r="4" fill="#111"/>
          <circle cx="74" cy="98" r="4" fill="#111"/>
          </g>
          <path d="M44 124 l8 -8 l8 8 l8 -8 l8 8" stroke="#fff" stroke-width="3" fill="none"/>`,
      );
    if (has(id, 'cartographer'))
      return svg(
        critter({
          species: 'cat',
          fur: '#f0a35e',
          patch: '#d9823a',
          coat: '#8b5a2b',
          hat: 'cap',
          hatColor: '#5a3a1a',
          extra: HELD.scroll,
        }),
      );
    if (has(id, 'guard'))
      return svg(
        critter({
          species: 'rabbit',
          fur: '#f5f2ee',
          coat: '#3d5a80',
          hat: 'helmet',
          extra: HELD.spear,
        }),
      );
    if (has(id, 'merchant'))
      return svg(
        critter({
          species: 'cat',
          fur: '#f4e1c1',
          patch: '#e09a4a',
          coat: '#a0522d',
          hat: 'turban',
          hatColor: '#e0a030',
          extra: HELD.sack,
        }),
      );
    if (has(id, 'librarian'))
      return svg(
        critter({
          species: 'rabbit',
          fur: '#a9a9b3',
          flop: true,
          coat: '#5e4b8b',
          hat: 'glasses',
          extra: HELD.book,
        }),
      );
    if (has(id, 'ranger'))
      return svg(
        critter({
          species: 'rabbit',
          fur: '#c8a27c',
          coat: '#2e6b3f',
          hat: 'hood',
          hatColor: '#1f4a2b',
          extra: HELD.bow,
        }),
      );
    if (has(id, 'innkeeper', 'keeper'))
      return svg(
        critter({
          species: 'cat',
          fur: '#b9bcc6',
          belly: '#f4f4f8',
          coat: '#b5651d',
          apron: true,
          extra: HELD.mug,
        }),
      );
    if (has(id, 'smith'))
      return svg(
        critter({
          species: 'cat',
          fur: '#cfeaff',
          belly: '#eef8ff',
          coat: '#7fb8d8',
          ghost: true,
          extra: HELD.hammer,
        }),
      );
    const hashValue = hash(id),
      species = hashValue % 2 ? 'rabbit' : 'cat';
    return svg(
      critter({
        species,
        fur: FUR[species][hashValue % 5],
        coat: `hsl(${hashValue % 360} 45% 40%)`,
      }),
    );
  }
  // Player skins depend ONLY on the player's name, so every client draws the same
  // player the same way: on every screen, in every room, in fights and in later
  // sessions. Names are case-insensitive on the server, so the name is lowercased.
  // (No protocol change is needed: any client using this rule agrees.)
  function skinFor(name) {
    let hashValue = 0x811c9dc5; // FNV-1a hash: stable and well spread
    for (const ch of String(name || '').toLowerCase())
      hashValue = Math.imul(hashValue ^ ch.codePointAt(0), 0x01000193) >>> 0;
    const species = hashValue & 1 ? 'rabbit' : 'cat';
    const fur = FUR[species][(hashValue >>> 1) % FUR[species].length];
    const coatHue = ((hashValue >>> 4) % 24) * 15;
    const capeHue = (coatHue + 120 + ((hashValue >>> 9) % 6) * 20) % 360;
    const patches = ['', '', '#d9823a', '#5a4a44', '#ffffff'];
    return {
      species,
      fur,
      patch: species === 'cat' ? patches[(hashValue >>> 13) % patches.length] : '',
      flop: species === 'rabbit' && ((hashValue >>> 16) & 3) === 0,
      coat: `hsl(${coatHue} 55% 42%)`,
      cape: `hsl(${capeHue} 50% 36%)`,
    };
  }

  function heroSprite(name) {
    return `<svg viewBox="0 -10 120 172" xmlns="http://www.w3.org/2000/svg">${critter({ ...skinFor(name), extra: HELD.sword })}</svg>`;
  }

  function itemIcon(id) {
    const svg = (inner) =>
      `<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
    if (has(id, 'compass'))
      return svg(
        `<circle cx="24" cy="24" r="18" fill="#c9d1db" stroke="#7d8794" stroke-width="3"/>
          <polygon points="24,9 28,24 20,24" fill="#d63a3a"/>
          <polygon points="24,39 28,24 20,24" fill="#fff"/>`,
      );
    if (has(id, 'key'))
      return svg(
        `<circle cx="14" cy="24" r="9" fill="none" stroke="#c87533" stroke-width="5"/>
          <rect x="22" y="22" width="22" height="5" fill="#c87533"/>
          <rect x="36" y="26" width="4" height="8" fill="#c87533"/>
          <rect x="30" y="26" width="4" height="6" fill="#c87533"/>`,
      );
    if (has(id, 'sword'))
      return svg(
        `<rect x="22" y="4" width="5" height="30" fill="#cfd5dc" transform="rotate(35 24 24)"/>
          <rect x="14" y="30" width="20" height="5" fill="#8a6b2f" transform="rotate(35 24 24)"/>
          <rect x="22" y="34" width="5" height="10" fill="#4a321d" transform="rotate(35 24 24)"/>`,
      );
    if (has(id, 'shield'))
      return svg(
        `<path d="M24 4 L42 10 Q42 34 24 44 Q6 34 6 10 Z" fill="#8f99a6" stroke="#4d5560" stroke-width="3"/>
          <circle cx="24" cy="22" r="5" fill="#c9a24a"/>`,
      );
    if (has(id, 'herb', 'leaf', 'plant'))
      return svg(
        `<path d="M24 44 V20" stroke="#2f6b2f" stroke-width="3"/>
          <ellipse cx="16" cy="20" rx="9" ry="5" fill="#4fbf5f" transform="rotate(-35 16 20)"/>
          <ellipse cx="32" cy="16" rx="9" ry="5" fill="#3fae4f" transform="rotate(35 32 16)"/>
          <ellipse cx="22" cy="10" rx="7" ry="4" fill="#6dd47c" transform="rotate(-70 22 10)"/>`,
      );
    if (has(id, 'bread', 'loaf', 'food'))
      return svg(
        `<ellipse cx="24" cy="28" rx="19" ry="12" fill="#c98a3d"/>
          <path d="M14 22 l4 8 M22 19 l4 8 M30 19 l4 8" stroke="#8a5a24" stroke-width="2"/>`,
      );
    if (has(id, 'lantern', 'lamp'))
      return svg(
        `<circle class="glow" cx="24" cy="28" r="16" fill="#ffd27a55"/>
          <rect x="16" y="16" width="16" height="22" rx="3" fill="#ffd27a" stroke="#4a3a2a" stroke-width="3"/>
          <path d="M18 16 Q24 6 30 16" fill="none" stroke="#4a3a2a" stroke-width="3"/>`,
      );
    if (has(id, 'map', 'scroll', 'note'))
      return svg(
        `<rect x="8" y="10" width="32" height="28" fill="#efe2bf" stroke="#b39b62" stroke-width="2"/>
          <path d="M12 18 h22 M12 24 h18 M12 30 h22" stroke="#9b8456" stroke-width="2"/>
          <path d="M28 20 l6 6" stroke="#c0392b" stroke-width="3"/>`,
      );
    if (has(id, 'lens', 'crystal', 'gem'))
      return svg(
        `<circle class="glow" cx="24" cy="24" r="18" fill="#9fd0ff44"/>
          <polygon points="24,6 38,20 30,42 18,42 10,20" fill="#9fd0ff" stroke="#e8f6ff" stroke-width="2"/>
          <path d="M24 6 L24 42 M10 20 H38" stroke="#e8f6ff" stroke-width="1"/>`,
      );
    if (has(id, 'heart'))
      return svg(
        `<circle class="glow" cx="24" cy="24" r="20" fill="#ff6b8b55"/>
          <path d="M24 40 C4 26 10 8 24 18 C38 8 44 26 24 40Z" fill="#ff4d6d" stroke="#ffd0da" stroke-width="2"/>`,
      );
    return svg(
      `<circle class="glow" cx="24" cy="24" r="18" fill="#fff5a844"/>
        <polygon points="24,8 30,22 24,40 18,22" fill="#ffe08a"/>`,
    );
  }

  // ------------------------------------------------------------------ scene state
  const state = {
    data: null,
    room: null,
    sig: '',
    bgKey: '',
    won: false,
    heroHp: 100,
    unlocked: new Set(),
    prevRoom: null,
    moveDir: null,
    npcPos: {},
    inventory: [],
  };

  function resolveNpc(arg) {
    const wanted = String(arg || '')
      .trim()
      .toLowerCase();
    for (const [id, npc] of Object.entries(cat().npcs || {}))
      if (
        id.toLowerCase() === wanted ||
        (npc.name || '').toLowerCase() === wanted ||
        id.replace(/^npc\./, '').toLowerCase() === wanted
      )
        return id;
    for (const id of state.data?.npcs || [])
      if (id.toLowerCase() === wanted || id.replace(/^npc\./, '').toLowerCase() === wanted)
        return id;
    return arg;
  }

  function closePopups() {
    for (const element of document.querySelectorAll('#sceneLayer .menu, #sceneLayer .bag'))
      element.remove();
  }

  function render(data) {
    state.data = data;
    const room = data.room || {};
    const sceneEl = byId('scene');
    if (!sceneEl) return;
    byId('sceneEmpty').classList.add('hide');
    byId('sceneTitle').textContent = room.name || room.id || 'Unknown place';
    byId('sceneDesc').textContent = room.description || '';
    const moved = room.id !== state.room;
    const sig = JSON.stringify([
      room.id,
      room.exits,
      data.npcs,
      data.items,
      data.players,
      state.won,
      [...state.unlocked],
    ]);
    if (sig === state.sig) return;
    state.sig = sig;
    if (moved) {
      state.room = room.id;
      closePopups();
      hideBubble();
    }
    const bgKey = room.id + '|' + state.won;
    if (bgKey !== state.bgKey) {
      state.bgKey = bgKey;
      const bg = byId('sceneBg');
      bg.innerHTML = roomArt(room.id || '', state.won);
      bg.classList.remove('enter');
      void bg.offsetWidth;
      bg.classList.add('enter');
    }
    // Actors: you, other players, NPCs and items on the ground.
    const actors = byId('sceneActors');
    actors.replaceChildren();
    const hero = actorEl('actor me', heroSprite(me()), 'You', 9, 12, 10);
    hero.title = 'You (' + me() + ')';
    hero.addEventListener('click', (clickEvent) => {
      clickEvent.stopPropagation();
      openBag();
    });
    if (moved && state.moveDir) {
      hero.classList.add('arrive-' + state.moveDir);
      state.moveDir = null;
    }
    actors.appendChild(hero);
    const others = (data.players || []).filter(
      (player) => player.toLowerCase() !== me().toLowerCase(),
    );
    others.slice(0, 4).forEach((player, index) => {
      const actor = actorEl('actor player', heroSprite(player), player, 19 + index * 7, 14, 7.5);
      actor.addEventListener('click', (clickEvent) => {
        clickEvent.stopPropagation();
        playerMenu(player, actor);
      });
      actors.appendChild(actor);
    });
    const npcs = data.npcs || [];
    state.npcPos = {};
    npcs.forEach((id, index) => {
      const info = cat().npcs?.[id] || {};
      const enemy = info.role === 'enemy';
      const boss = has(id, 'warden', 'boss');
      const left = npcs.length === 1 ? 64 : 40 + index * (50 / Math.max(1, npcs.length - 1));
      const actor = actorEl(
        'actor npc' + (enemy ? ' enemy' : '') + (info.role === 'quest_giver' ? ' giver' : ''),
        npcSprite(id),
        nameOf('npcs', id),
        left,
        13,
        boss ? 15 : 10.5,
      );
      actor.dataset.npc = id;
      if (info.role === 'quest_giver') actor.prepend(el('span', 'mark', '✦'));
      if (enemy) actor.prepend(el('span', 'mark', '⚔'));
      actor.addEventListener('click', (clickEvent) => {
        clickEvent.stopPropagation();
        npcMenu(id, actor);
      });
      state.npcPos[id] = left;
      actors.appendChild(actor);
    });
    (data.items || []).forEach((id, index) => {
      const actor = actorEl(
        'actor item',
        itemIcon(id),
        nameOf('items', id),
        22 + index * 7,
        3,
        4.6,
      );
      actor.title = 'Click to TAKE ' + nameOf('items', id);
      actor.addEventListener('click', (clickEvent) => {
        clickEvent.stopPropagation();
        actor.classList.add('picked');
        setTimeout(() => act('TAKE ' + id), 200);
      });
      actors.appendChild(actor);
    });
    // Exits around the edges of the picture.
    const exits = byId('sceneExits');
    exits.replaceChildren();
    for (const dir of DIRS) {
      const dest = room.exits?.[dir];
      if (!dest) continue;
      const lockItem = cat().rooms?.[room.id]?.locks?.[dir];
      const locked = lockItem && !state.unlocked.has(room.id + '>' + dir);
      const exitButton = el('button', 'exit ' + dir + (locked ? ' locked' : ''));
      exitButton.dataset.dir = dir;
      exitButton.title = locked
        ? 'Locked. You need the ' + nameOf('items', lockItem) + ' to go ' + dir + '.'
        : 'Move ' + dir;
      exitButton.append(
        el('span', 'arrow', ARROW[dir]),
        el(
          'span',
          '',
          dir[0].toUpperCase() +
            dir.slice(1) +
            ' to ' +
            nameOf('rooms', dest) +
            (locked ? ', locked' : ''),
        ),
      );
      exitButton.addEventListener('click', () => walk(dir));
      exits.appendChild(exitButton);
    }
  }

  function actorEl(cls, svg, label, leftPct, bottomPct, widthPct) {
    const actor = el('button', cls);
    actor.type = 'button';
    actor.style.left = leftPct + '%';
    actor.style.bottom = bottomPct + '%';
    actor.style.width = widthPct + '%';
    const sp = el('div', 'sprite');
    sp.innerHTML = svg;
    actor.append(sp, el('span', 'tag', label));
    return actor;
  }

  function walk(dir) {
    closePopups();
    hideBubble();
    const hero = document.querySelector('#sceneActors .actor.me');
    state.moveDir = OPPOSITE[dir];
    if (hero) {
      hero.classList.add('walk-' + dir);
      setTimeout(() => act('MOVE ' + dir), 280);
    } else act('MOVE ' + dir);
  }

  // ------------------------------------------------------------------ popups
  function popup(anchor, build, cls = 'menu') {
    closePopups();
    const layer = byId('sceneLayer');
    const menu = el('div', cls);
    build(menu);
    if (cls === 'menu') {
      const left = parseFloat(anchor.style.left) || 50;
      menu.style.left = Math.min(84, Math.max(16, left)) + '%';
      menu.style.bottom = '48%';
    }
    layer.appendChild(menu);
    menu.addEventListener('click', (clickEvent) => clickEvent.stopPropagation());
    return menu;
  }

  function button(text, onClick, cls = '') {
    const buttonElement = el('button', cls, text);
    buttonElement.type = 'button';
    buttonElement.addEventListener('click', onClick);
    return buttonElement;
  }

  function npcMenu(id, anchor) {
    const info = cat().npcs?.[id] || {};
    popup(anchor, (menu) => {
      menu.append(
        el('h4', '', nameOf('npcs', id)),
        el(
          'p',
          '',
          (info.description || id) +
            (info.role === 'enemy' ? ` (HP ${info.hp}, attack ${info.attack})` : ''),
        ),
      );
      const acts = el('div', 'acts');
      const enemy = info.role === 'enemy',
        known = !!info.role;
      acts.append(
        button('Talk', () => {
          closePopups();
          act('TALK ' + id);
        }),
      );
      if (!enemy)
        acts.append(
          button('Quest', () => {
            closePopups();
            act('QUEST ' + id);
          }),
        );
      if (enemy || !known)
        acts.append(
          button(
            'Attack',
            () => {
              closePopups();
              act('ATTACK ' + id);
            },
            'danger',
          ),
        );
      acts.append(button('✕', closePopups, 'close'));
      menu.appendChild(acts);
    });
  }

  function playerMenu(name, anchor) {
    popup(anchor, (menu) => {
      menu.append(el('h4', '', name), el('p', '', 'Another adventurer.'));
      const acts = el('div', 'acts');
      acts.append(
        button('Wave', () => {
          closePopups();
          act('CHAT ROOM Hi ' + name + '!');
        }),
        button('Invite to group', () => {
          closePopups();
          act('GROUP INVITE ' + name);
        }),
        button('Join group', () => {
          closePopups();
          act('GROUP JOIN ' + name);
        }),
        button('✕', closePopups, 'close'),
      );
      menu.appendChild(acts);
    });
  }

  function usable(id) {
    const it = cat().items?.[id];
    return !it || it.heal > 0;
  }

  function openBag() {
    popup(
      null,
      (menu) => {
        menu.appendChild(el('h4', '', 'Your bag'));
        if (!state.inventory.length)
          menu.appendChild(
            el(
              'p',
              'subtitle',
              'Your pockets are empty. Click items on the ground to pick them up.',
            ),
          );
        for (const id of state.inventory) {
          const row = el('div', 'row');
          const name = el('span');
          name.innerHTML = itemIcon(id);
          name.append(nameOf('items', id));
          const btns = el('span');
          if (usable(id))
            btns.append(
              button('Use', () => {
                closePopups();
                act('USE ' + id);
              }),
            );
          btns.append(
            button('Drop', () => {
              closePopups();
              act('DROP ' + id);
            }),
          );
          row.append(name, btns);
          menu.appendChild(row);
        }
        menu.appendChild(button('Close', closePopups));
      },
      'bag',
    );
  }
  let bubbleTimer = 0;

  function bubble(npcId, text) {
    hideBubble();
    const left = state.npcPos[npcId];
    if (left === undefined) return;
    const speech = el('div', 'bubble');
    speech.append(el('b', '', nameOf('npcs', npcId)), document.createTextNode(text));
    speech.style.left = Math.min(78, Math.max(22, left)) + '%';
    speech.style.bottom = (has(npcId, 'warden') ? 64 : 52) + '%';
    speech.addEventListener('click', hideBubble);
    byId('sceneLayer').appendChild(speech);
    bubbleTimer = setTimeout(hideBubble, Math.min(14000, 4000 + text.length * 45));
  }

  function hideBubble() {
    clearTimeout(bubbleTimer);
    for (const oldBubble of document.querySelectorAll('#sceneLayer .bubble')) oldBubble.remove();
  }

  function caption(text) {
    const box = byId('sceneCaptions');
    if (!box) return;
    for (const previous of box.children) previous.classList.add('old');
    box.appendChild(el('div', '', text));
    while (box.children.length > 3) box.firstChild.remove();
  }

  function shakeActor(sel) {
    const actor = document.querySelector(sel);
    if (actor) {
      actor.classList.remove('shake');
      void actor.offsetWidth;
      actor.classList.add('shake');
    }
  }

  // ------------------------------------------------------------------ combat
  const fight = {
    open: false,
    npc: null,
    max: 1,
    hp: 0,
    over: false,
    timer: 0,
    helpers: new Set(),
  };

  function fighterEls() {
    return { hero: byId('fHero'), foe: byId('fFoe') };
  }

  function openFight(npc, hpBefore) {
    const info = cat().npcs?.[npc] || {};
    fight.open = true;
    fight.npc = npc;
    fight.over = false;
    fight.helpers = new Set();
    fight.max = info.hp || Math.max(hpBefore || 1, 1);
    fight.hp = hpBefore ?? fight.max;
    const screen = byId('combat');
    screen.classList.remove('hide', 'closing');
    screen.innerHTML = '';
    const title = el('div', 'combat-title', 'Fight with the ' + nameOf('npcs', npc));
    const arena = el('div', 'arena');
    const hero = el('div', 'fighter me-f');
    hero.id = 'fHero';
    const foe = el('div', 'fighter foe' + (has(npc, 'warden', 'boss') ? ' boss' : ''));
    foe.id = 'fFoe';
    for (const [fighter, svg, name] of [
      [hero, heroSprite(me()), 'You'],
      [foe, npcSprite(npc), nameOf('npcs', npc)],
    ]) {
      const bar = el('div', 'hp');
      bar.appendChild(el('i'));
      const sp = el('div', 'sprite');
      sp.innerHTML = svg;
      fighter.append(bar, el('span', 'hp-text'), sp, el('span', 'name', name));
    }
    arena.append(hero, el('div', 'vs', 'VS'), foe);
    const acts = el('div', 'combat-actions');
    acts.id = 'combatActions';
    acts.append(
      button('Attack', () => combatCmd('ATTACK ' + fight.npc), 'atk'),
      button('Defend', () => combatCmd('DEFEND')),
      button('Use item', () => {
        const heal =
          state.inventory.find((id) => usable(id) && cat().items?.[id]?.heal > 0) ||
          state.inventory.find(usable);
        if (heal) combatCmd('USE ' + heal);
        else caption('You have no healing item. Healing Herbs grow in the Glass Garden.');
      }),
      button('Flee', () => combatCmd('FLEE'), 'flee'),
    );
    screen.append(title, arena, acts);
    bars();
  }

  function combatCmd(line) {
    if (fight.busy) return;
    busy(true);
    act(line);
    fight.timer = setTimeout(() => busy(false), 1500);
  }

  function busy(on) {
    fight.busy = on;
    for (const actionButton of document.querySelectorAll('#combatActions button'))
      actionButton.disabled = on;
    if (!on) clearTimeout(fight.timer);
  }

  function bars() {
    const { hero, foe } = fighterEls();
    if (!hero) return;
    const set = (fighter, hp, max) => {
      const pct = Math.max(0, Math.min(100, (hp / max) * 100));
      fighter.querySelector('.hp i').style.width = pct + '%';
      fighter.querySelector('.hp').classList.toggle('low', pct < 30);
      fighter.querySelector('.hp-text').textContent = Math.max(0, hp) + ' / ' + max + ' HP';
    };
    set(hero, state.heroHp, 100);
    set(foe, fight.hp, fight.max);
  }

  function anim(fighter, cls, ms = 450) {
    if (!fighter) return;
    fighter.classList.remove(cls);
    void fighter.offsetWidth;
    fighter.classList.add(cls);
    setTimeout(() => fighter.classList.remove(cls), ms);
  }

  function floatText(fighter, text, kind = '') {
    if (!fighter) return;
    const label = el('span', 'float ' + kind, text);
    fighter.appendChild(label);
    setTimeout(() => label.remove(), 1000);
  }

  function attackResult(npc, serverReply) {
    if (!fight.open || fight.npc !== npc || fight.over)
      openFight(npc, serverReply.target_hp + serverReply.damage);
    const { hero, foe } = fighterEls();
    anim(hero, 'lunge-r', 350);
    setTimeout(() => {
      anim(foe, 'hit');
      floatText(foe, '-' + serverReply.damage);
      fight.hp = serverReply.target_hp;
      bars();
      if (serverReply.status === 'victory') {
        setTimeout(() => foeDefeated(null), 350);
        return;
      }
      setTimeout(() => {
        anim(foe, 'lunge-l', 350);
        setTimeout(() => {
          anim(hero, 'hit');
          floatText(hero, '-' + serverReply.counter_damage);
          state.heroHp = serverReply.status === 'respawn' ? 0 : serverReply.attacker_hp;
          bars();
          if (serverReply.status === 'respawn') heroDefeated();
          else busy(false);
        }, 220);
      }, 320);
    }, 230);
  }

  function defendResult(serverReply) {
    if (!fight.open) return;
    const { hero, foe } = fighterEls();
    anim(hero, 'guard', 600);
    floatText(hero, '🛡', 'info');
    setTimeout(() => {
      anim(foe, 'lunge-l', 350);
      setTimeout(() => {
        anim(hero, 'hit');
        floatText(hero, '-' + serverReply.damage_taken);
        state.heroHp = serverReply.hp;
        bars();
        busy(false);
      }, 220);
    }, 350);
  }

  function useResult(serverReply) {
    if (!fight.open || fight.over) {
      state.heroHp = serverReply.hp;
      const heroActor = document.querySelector('#sceneActors .actor.me');
      if (heroActor) {
        heroActor.classList.remove('healed');
        void heroActor.offsetWidth;
        heroActor.classList.add('healed');
      }
      return;
    }
    const { hero, foe } = fighterEls();
    anim(hero, 'healed', 900);
    floatText(hero, '+' + serverReply.healed, 'heal');
    state.heroHp = serverReply.hp + (serverReply.counter_damage || 0);
    bars();
    if (serverReply.counter_damage > 0)
      setTimeout(() => {
        anim(foe, 'lunge-l', 350);
        setTimeout(() => {
          anim(hero, 'hit');
          floatText(hero, '-' + serverReply.counter_damage);
          state.heroHp = serverReply.hp;
          bars();
          busy(false);
        }, 220);
      }, 500);
    else busy(false);
  }

  function result(win, title, lines) {
    fight.over = true;
    busy(false);
    const acts = byId('combatActions');
    if (acts) acts.classList.add('hide');
    const box = el('div', 'combat-result' + (win ? '' : ' lose'));
    box.id = 'combatResult';
    const inner = el('div', 'box');
    inner.append(el('h3', '', title));
    for (const line of lines) inner.appendChild(el('p', '', line));
    const extra = el('div', 'extra');
    extra.id = 'combatExtra';
    inner.append(extra, button('Continue', closeFight, 'primary'));
    box.appendChild(inner);
    byId('combat').appendChild(box);
    if (win) confetti(byId('combat'));
  }

  function foeDefeated(by) {
    const { foe } = fighterEls();
    if (foe) foe.classList.add('dead');
    const name = nameOf('npcs', fight.npc);
    const helpers = [...fight.helpers].filter((helper) => helper !== by);
    const lines = by
      ? [
          `${by} landed the final blow on the ${name}. Well fought, team!`,
          `Quests to defeat the ${name} are completed by the player who lands the final blow.`,
        ]
      : [
          `You defeated the ${name}!` +
            (helpers.length ? ` Thanks to ${helpers.join(', ')} for the help.` : ''),
        ];
    setTimeout(() => result(true, by ? 'Team victory!' : 'Victory!', lines), 650);
  }

  function heroDefeated() {
    const { hero } = fighterEls();
    if (hero) hero.classList.add('fallen');
    setTimeout(
      () =>
        result(false, 'Defeated', [
          'You were knocked out...',
          'You wake up in the safe square with 35 HP. Your items and quests are safe.',
        ]),
      700,
    );
  }

  function fleeResult() {
    if (!fight.open) return;
    const { hero } = fighterEls();
    if (hero) hero.classList.add('run');
    setTimeout(closeFight, 600);
  }

  function invulnerable(npc) {
    openFight(npc);
    const { hero, foe } = fighterEls();
    anim(hero, 'lunge-r', 350);
    setTimeout(() => {
      anim(foe, 'immune', 600);
      floatText(foe, 'IMMUNE', 'info');
    }, 230);
    const quest = cat().npcs?.[npc]?.requires_quest;
    setTimeout(
      () =>
        result(false, 'Invulnerable', [
          `Your blows pass straight through the ${nameOf('npcs', npc)}!`,
          quest
            ? `Complete the quest "${cat().quests?.[quest]?.name || quest}" first.`
            : 'You need to grow stronger first.',
        ]),
      900,
    );
  }

  function closeFight() {
    const screen = byId('combat');
    if (!fight.open) return;
    fight.open = false;
    fight.over = false;
    busy(false);
    screen.classList.add('closing');
    setTimeout(() => {
      screen.classList.add('hide');
      screen.classList.remove('closing');
      screen.innerHTML = '';
    }, 380);
  }

  function confetti(host) {
    const colors = ['#c9a24a', '#8fcfb5', '#ece3cc', '#d9695f', '#e6c77a'];
    for (let index = 0; index < 40; index++) {
      const piece = el('span', 'confetti');
      piece.style.left = Math.random() * 100 + '%';
      piece.style.background = colors[index % colors.length];
      piece.style.setProperty('--x', Math.random() * 160 - 80 + 'px');
      piece.style.setProperty('--r', Math.random() * 720 + 'deg');
      piece.style.animationDelay = Math.random() * 0.4 + 's';
      host.appendChild(piece);
      setTimeout(() => piece.remove(), 2400);
    }
  }

  // ------------------------------------------------------------------ protocol hooks
  function reply(command, line) {
    const sp = command.indexOf(' ');
    const cmd = (sp < 0 ? command : command.slice(0, sp)).toUpperCase();
    const arg = sp < 0 ? '' : command.slice(sp + 1).trim();
    const ok = line === 'OK' || line.startsWith('OK ');
    const err = line.startsWith('ERR ') ? line.split(' ').slice(2).join(' ') : '';
    switch (cmd) {
      case 'ATTACK': {
        const npc = resolveNpc(arg);
        if (ok) {
          const serverReply = parseJSON(line);
          if (serverReply) attackResult(npc, serverReply);
        } else if (err === 'NPC_INVULNERABLE') invulnerable(npc);
        else {
          busy(false);
          if (!fight.open) shakeActor(`#sceneActors [data-npc="${CSS.escape(npc)}"]`);
        }
        break;
      }
      case 'DEFEND':
        if (ok) {
          const serverReply = parseJSON(line);
          if (serverReply) defendResult(serverReply);
        } else busy(false);
        break;
      case 'USE':
        if (ok) {
          const serverReply = parseJSON(line);
          if (serverReply) useResult(serverReply);
        } else busy(false);
        break;
      case 'FLEE':
        if (ok) {
          state.moveDir = null;
          fleeResult();
        } else busy(false);
        break;
      case 'MOVE':
        if (ok) state.prevRoom = state.room;
        else {
          state.moveDir = null;
          const hero = document.querySelector('#sceneActors .actor.me');
          if (hero) hero.className = 'actor me';
          const exitButton = document.querySelector(
            `#sceneExits .exit.${CSS.escape(arg.toLowerCase())}`,
          );
          if (exitButton) {
            exitButton.classList.remove('denied');
            void exitButton.offsetWidth;
            exitButton.classList.add('denied');
          }
        }
        break;
      case 'TALK':
        if (ok) bubble(resolveNpc(arg), line.slice(3));
        break;
      case 'QUEST': {
        const npc = resolveNpc(arg);
        if (ok) {
          const quest = parseJSON(line);
          if (quest)
            bubble(
              npc,
              `Quest "${quest.name || quest.quest_id}" (${quest.status}). ${quest.description || ''}`,
            );
        } else if (err === 'NO_QUEST_AVAILABLE')
          bubble(npc, 'I have no quest for you right now. Talk to me for a hint.');
        break;
      }
    }
  }

  function event(line) {
    let match;
    if ((match = /^EVT ROOM COMBAT (\S+) (\S+) (.*)$/.exec(line))) {
      const [, who, npc, rest] = match;
      if (who.toLowerCase() === me().toLowerCase() || npc === 'DEFEND') return;
      const kv = Object.fromEntries(rest.split(' ').map((pair) => pair.split('=')));
      if (fight.open && fight.npc === npc && !fight.over) {
        const { foe } = fighterEls();
        fight.helpers.add(who);
        anim(foe, 'hit');
        floatText(foe, `-${kv.damage} (${who})`, 'other');
        fight.hp = +kv.target_hp;
        bars();
        if (kv.status === 'victory') foeDefeated(who);
      } else shakeActor(`#sceneActors [data-npc="${CSS.escape(npc)}"]`);
    } else if ((match = /^EVT ROOM ITEM LOOT (\S+) (\S+)/.exec(line))) {
      const box = byId('combatExtra');
      if (box)
        box.appendChild(
          el(
            'p',
            '',
            `The ${nameOf('npcs', match[1])} dropped the ${nameOf('items', match[2])}. Pick it up from the ground.`,
          ),
        );
    } else if ((match = /^EVT QUEST COMPLETE (\S+)/.exec(line))) {
      const box = byId('combatExtra');
      if (box)
        box.appendChild(
          el('p', '', `Quest complete: ${cat().quests?.[match[1]]?.name || match[1]}`),
        );
      confetti(byId('scene'));
    } else if ((match = /^EVT PLAYER UNLOCK (\S+)/.exec(line))) {
      if (state.prevRoom) state.unlocked.add(state.prevRoom + '>' + match[1]);
    } else if (line.startsWith('EVT PLAYER RESPAWN')) {
      state.heroHp = 35;
      if (fight.open && !fight.over) {
        state.heroHp = 0;
        bars();
        heroDefeated();
      }
    } else if (
      (match = /^EVT GLOBAL VICTORY (\S+)/.exec(line)) &&
      match[1].toLowerCase() === me().toLowerCase()
    ) {
      state.won = true;
      state.sig = '';
      if (state.data) render(state.data);
      confetti(byId('scene'));
      setTimeout(() => confetti(byId('scene')), 700);
    }
  }

  function status(data) {
    if (data.hp !== undefined && !(fight.open && !fight.over)) state.heroHp = data.hp;
    if (data.victory !== undefined && !!data.victory !== state.won) {
      state.won = !!data.victory;
      state.sig = '';
      if (state.data) render(state.data);
    }
    if (fight.open) bars();
  }

  function reset() {
    Object.assign(state, {
      data: null,
      room: null,
      sig: '',
      bgKey: '',
      won: false,
      heroHp: 100,
      unlocked: new Set(),
      prevRoom: null,
      moveDir: null,
      npcPos: {},
      inventory: [],
    });
    fight.open = false;
    const screen = byId('combat');
    if (screen) {
      screen.classList.add('hide');
      screen.innerHTML = '';
    }
    for (const id of ['sceneBg', 'sceneActors', 'sceneExits', 'sceneCaptions']) {
      const element = byId(id);
      if (element) element.replaceChildren();
    }
    closePopups();
    hideBubble();
    const empty = byId('sceneEmpty');
    if (empty) empty.classList.remove('hide');
    const title = byId('sceneTitle');
    if (title) title.textContent = 'Scene';
    const description = byId('sceneDesc');
    if (description) description.textContent = '';
  }

  function init() {
    const scene = byId('scene');
    if (!scene) return;
    scene.addEventListener('click', () => {
      closePopups();
    });
    for (const sceneButton of document.querySelectorAll('[data-scene]'))
      sceneButton.addEventListener('click', (clickEvent) => {
        clickEvent.stopPropagation();
        if (sceneButton.dataset.scene === 'BAG') openBag();
        else act(sceneButton.dataset.scene);
      });
    const say = byId('sceneSay');
    if (say)
      say.addEventListener('submit', (submitEvent) => {
        submitEvent.preventDefault();
        const input = byId('sceneSayText');
        const text = input.value.trim();
        if (text) act('CHAT ROOM ' + text);
        input.value = '';
      });
  }
  window.Scene = {
    art: roomArt,
    npcSprite,
    heroSprite,
    skinFor,
    itemIcon,
    room: render,
    inventory: (ids) => {
      state.inventory = ids;
    },
    status,
    reply,
    event,
    caption,
    reset,
    closeFight,
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
