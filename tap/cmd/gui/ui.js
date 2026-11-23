// TAP browser client: connection, command queue, map, quest journal and chat.
// The illustrated scene and combat screen live in scene.js, which is loaded first.
'use strict';
let playerName = '',
  sessionID = '',
  stream = null,
  scope = 'GLOBAL',
  catalog = { items: {}, npcs: {}, rooms: {} },
  currentRoom = null,
  active = true;
let sendChain = Promise.resolve(),
  commandQueue = [],
  lastChat = { GLOBAL: [], ROOM: [], GROUP: [] },
  unread = { GLOBAL: 0, ROOM: 0, GROUP: 0 };
const byId = (id) => document.getElementById(id);
// Panels can be removed from the page: these helpers skip elements that no longer exist.
const on = (id, type, handler) => {
  const element = byId(id);
  if (element) element.addEventListener(type, handler);
};
const setText = (id, text) => {
  const element = byId(id);
  if (element) element.textContent = text;
};

function labelFor(type, id) {
  return catalog[type]?.[id]?.name || id.replace(/^(item|npc|loc)\./, '').replaceAll('_', ' ');
}

function logLine(text, kind = '') {
  const entry = document.createElement('div');
  entry.className = kind;
  entry.textContent = text;
  byId('protocolLog').appendChild(entry);
  byId('protocolLog').scrollTop = byId('protocolLog').scrollHeight;
  while (byId('protocolLog').children.length > 200) byId('protocolLog').firstChild.remove();
}

function clock() {
  return new Date().toLocaleTimeString('en-GB', { hour12: false });
}

function appendChat(kind, txt) {
  lastChat[kind].push({ time: clock(), text: txt });
  if (lastChat[kind].length > 200) lastChat[kind].shift();
  if (kind !== scope) unread[kind]++;
  renderChat();
}

function chatTarget() {
  return scope;
}

function renderTabs() {
  for (const tab of byId('chatTabs').children) {
    const tabScope = tab.dataset.scope;
    tab.setAttribute('aria-selected', String(tabScope === scope));
    tab.textContent = tabScope[0] + tabScope.slice(1).toLowerCase();
    if (unread[tabScope]) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = '(' + unread[tabScope] + ')';
      tab.appendChild(badge);
    }
  }
  byId('chatMessage').placeholder = 'Write a ' + chatTarget().toLowerCase() + ' chat message...';
}

function renderChat() {
  unread[scope] = 0;
  renderTabs();
  const el = byId('chatLog');
  el.replaceChildren();
  const lines = lastChat[scope];
  if (!lines.length) {
    el.textContent = 'No ' + scope.toLowerCase() + ' messages yet.';
    return;
  }
  for (const line of lines) {
    const entry = document.createElement('div');
    if (/^(You|Your|Welcome)\b/.test(line.text)) entry.className = 'self';
    const timeLabel = document.createElement('span');
    timeLabel.className = 'time';
    timeLabel.textContent = line.time;
    entry.append(timeLabel, line.text);
    el.appendChild(entry);
  }
  el.scrollTop = el.scrollHeight;
}

function setOnline(ok) {
  if (!ok) {
    window.Scene?.reset();
    for (const [id, resetValue] of [
      ['roomPlayers', 0],
      ['serverPlayers', 0],
      ['health', 100],
      ['gold', 0],
      ['attack', '—'],
      ['defense', '—'],
    ])
      setText(id, resetValue);
    byId('health')?.closest('.hud-item')?.classList.remove('low');
    setHealthBar(100, 100);
    byId('champBadge')?.classList.add('hide');
    byId('wherePill').textContent = 'Not in the world';
    byId('mapWhere').textContent = 'Not connected';
  }
  active = ok;
  byId('quitBtn')?.classList.toggle('hide', !ok);
  const statusPill = byId('connectionStatus');
  statusPill.textContent = ok ? 'Connected' : 'Disconnected';
  statusPill.classList.toggle('online', ok);
  byId('connectPanel').classList.toggle('hide', ok);
}

// Width of the HP bar in the header, as a share of the maximum health.
function setHealthBar(health, maxHealth) {
  const fill = byId('hpFill');
  if (!fill) return;
  const share = maxHealth > 0 ? Math.max(0, Math.min(1, health / maxHealth)) : 0;
  fill.style.width = Math.round(share * 100) + '%';
}

async function api(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || data.error || 'HTTP ' + res.status);
  return data;
}

async function connect(name) {
  byId('connectError').textContent = '';
  try {
    const reply = await api('/api/connect', { name });
    window.Scene?.reset();
    sessionID = reply.id;
    playerName = name;
    byId('victoryPanel').classList.add('hide');
    setOnline(true);
    logLine('OK connected as ' + name);
    if (stream) stream.close();
    stream = new EventSource('/api/events?id=' + encodeURIComponent(sessionID));
    stream.onmessage = (event) => onServerLine(event.data);
    stream.addEventListener('narration', (event) => window.Scene?.caption(event.data));
    stream.addEventListener('map', (event) => {
      try {
        renderMap(JSON.parse(event.data));
      } catch (err) {
        logLine('Bad map update: ' + err.message, 'err');
      }
    });
    stream.onerror = () => logLine('SSE connection interrupted; retrying automatically.', 'err');
    await refresh();
  } catch (err) {
    byId('connectError').textContent = err.message;
    logLine(err.message, 'err');
    setOnline(false);
  }
}
// quiet=true: automatic refreshes; the reply updates the UI but is not narrated under the scene.
async function send(line, quiet = false) {
  if (!line) return;
  if (!sessionID || !active) {
    logLine('Not connected.', 'err');
    if (!quiet)
      setText('connectError', 'You are not connected. Enter a username and press Connect.');
    return;
  }
  const entry = { line, quiet },
    id = sessionID;
  commandQueue.push(entry);
  if (!quiet) logLine('> ' + line);
  // Commands are posted strictly one after another: parallel requests could reach the
  // server out of order and replies would then be matched to the wrong command.
  const job = sendChain
    .then(() => api('/api/send', { id, line, quiet }))
    .catch((err) => {
      const pos = commandQueue.indexOf(entry);
      if (pos >= 0) commandQueue.splice(pos, 1);
      logLine(err.message, 'err');
      if (!quiet) window.Scene?.caption('Your command could not be sent: ' + err.message);
    });
  sendChain = job;
  return job;
}

function parseJSON(line) {
  try {
    return JSON.parse(line.slice(3));
  } catch {
    return null;
  }
}

function onServerLine(line) {
  if (line.startsWith('EVT ')) {
    handleEvent(line);
    return;
  }
  if (line === 'ERR 900 CONNECTION_FAILED') {
    logLine(line, 'err');
    disconnect(false);
    return;
  }
  const entry = commandQueue.shift() || { line: '?', quiet: false },
    command = entry.line;
  if (!entry.quiet || line.startsWith('ERR')) logLine(line, line.startsWith('ERR') ? 'err' : '');
  try {
    window.Scene?.reply(command, line);
  } catch (err) {
    console.error(err);
  }
  if (line === 'OK bye') {
    disconnect(false);
    return;
  }
  if (!line.startsWith('OK ')) return;
  if (command === 'LOOK') {
    const data = parseJSON(line);
    if (data && data.room) renderRoom(data);
  } else if (command === 'INVENTORY') {
    const data = parseJSON(line);
    if (Array.isArray(data)) renderInventory(data);
  } else if (command === 'STATUS') {
    const data = parseJSON(line);
    if (data) {
      setText('health', data.hp ?? '?');
      setText('maxHp', '/' + (data.max_hp ?? 100));
      byId('health')
        ?.closest('.hud-item')
        ?.classList.toggle('low', data.hp < (data.max_hp ?? 100) / 2);
      setHealthBar(data.hp, data.max_hp ?? 100);
      setText('gold', data.gold ?? '0');
      if (data.attack !== undefined) {
        setText('attack', data.attack);
        setText('defense', data.defense ?? 0);
      }
      byId('champBadge')?.classList.toggle('hide', !data.victory);
      if (data.victory) showVictory();
      window.Scene?.status(data);
    }
  } else if (command === 'WHO') {
    const value = /^OK players=(\d+)/.exec(line);
    if (value) setText('serverPlayers', value[1]);
    else {
      const data = parseJSON(line);
      if (data?.server !== undefined) setText('serverPlayers', data.server);
    }
  } else if (
    command.startsWith('MOVE ') ||
    command.startsWith('FLEE') ||
    command.startsWith('TAKE ') ||
    command.startsWith('DROP ') ||
    command.startsWith('ATTACK ') ||
    command.startsWith('TALK ') ||
    command.startsWith('QUEST ') ||
    command.startsWith('USE ') ||
    command === 'DEFEND'
  )
    refresh();
  else if (command.startsWith('QUESTS')) {
    const data = parseJSON(line);
    if (Array.isArray(data)) renderJournal(data);
  }
}

function handleEvent(line) {
  try {
    window.Scene?.event(line);
  } catch (err) {
    console.error(err);
  }
  if (
    line.startsWith('EVT GLOBAL CHAT ') ||
    line.startsWith('EVT ROOM CHAT ') ||
    line.startsWith('EVT GROUP CHAT ')
  ) {
    const match = /^EVT (GLOBAL|ROOM|GROUP) CHAT (.*)$/.exec(line);
    if (match) {
      appendChat(match[1], match[2]);
      return;
    }
  }
  logLine(line, 'evt');
  const count = /^EVT STATS players=(\d+)/.exec(line);
  if (count) {
    setText('serverPlayers', count[1]);
    return;
  }
  if (
    line.startsWith('EVT ROOM PRESENCE') ||
    line.startsWith('EVT ROOM ITEM') ||
    line.startsWith('EVT ROOM NPC') ||
    line.startsWith('EVT PLAYER RESPAWN')
  )
    send('LOOK', true);
  if (line.startsWith('EVT QUEST') || line.startsWith('EVT PLAYER RESPAWN')) {
    send('QUESTS', true);
    send('STATUS', true);
  }
  if (line.startsWith('EVT ROOM COMBAT')) send('STATUS', true);
  const win = /^EVT GLOBAL VICTORY (\S+)/.exec(line);
  if (win && win[1].toLowerCase() === playerName.toLowerCase()) {
    showVictory();
    send('STATUS', true);
    send('QUESTS', true);
  }
}

function renderRoom(data) {
  try {
    window.Scene?.room(data);
  } catch (err) {
    console.error(err);
  }
  currentRoom = data.room;
  setText('roomPlayers', (data.players || []).length);
}

// ---- Map (layout computed by the Go bridge, package worldmap) ----
const SVG = 'http://www.w3.org/2000/svg',
  CW = 150,
  CH = 56,
  GX = 46,
  GY = 40,
  PAD = 18,
  DIRS = ['north', 'east', 'south', 'west'];

function svgEl(tag, attrs, parent) {
  const element = document.createElementNS(SVG, tag);
  for (const [attribute, value] of Object.entries(attrs)) element.setAttribute(attribute, value);
  if (parent) parent.appendChild(element);
  return element;
}

function wrapName(name, max = 18) {
  if (name.length <= max) return [name];
  const words = name.split(' ');
  let firstLine = '';
  while (words.length && (firstLine + ' ' + words[0]).trim().length <= max)
    firstLine = (firstLine + ' ' + words.shift()).trim();
  if (!firstLine) return [name.slice(0, max - 1) + '…'];
  let secondLine = words.join(' ');
  if (secondLine.length > max) secondLine = secondLine.slice(0, max - 1) + '…';
  return secondLine ? [firstLine, secondLine] : [firstLine];
}

function renderMap(map) {
  const view = byId('mapView');
  view.replaceChildren();
  if (!map || !map.rooms || !map.rooms.length) {
    view.innerHTML =
      '<div class="empty">Map unknown. Use LOOK to discover your surroundings.</div>';
    return;
  }
  const exits = Object.keys(map.exits || {}).sort(
    (first, second) => DIRS.indexOf(first) - DIRS.indexOf(second),
  );
  const where = map.current_name || 'unknown';
  byId('wherePill').textContent = where;
  byId('wherePill').title = 'You are in ' + where;
  byId('mapWhere').textContent =
    'You are in ' + where + (exits.length ? '. Exits: ' + exits.join(', ') + '.' : '.');
  const long = map.links.some((link) => link.kind === 'long');
  const width = PAD * 2 + map.width * CW + (map.width - 1) * GX,
    height = PAD * 2 + map.height * CH + (map.height - 1) * GY + (long ? 44 : 0);
  const svg = svgEl('svg', {
    viewBox: '0 0 ' + width + ' ' + height,
    role: 'img',
    'aria-label': 'World map. You are in ' + where,
  });
  const pos = {};
  for (const room of map.rooms)
    pos[room.id] = { x: PAD + room.x * (CW + GX), y: PAD + room.y * (CH + GY) };
  const center = (id) => ({ x: pos[id].x + CW / 2, y: pos[id].y + CH / 2 });
  for (const link of map.links) {
    const fromCenter = center(link.a),
      toCenter = center(link.b);
    if (link.kind === 'long') {
      const low = height - 14,
        pathData =
          'M' +
          fromCenter.x +
          ' ' +
          fromCenter.y +
          ' C' +
          fromCenter.x +
          ' ' +
          low +
          ' ' +
          toCenter.x +
          ' ' +
          low +
          ' ' +
          toCenter.x +
          ' ' +
          toCenter.y;
      const path = svgEl('path', { d: pathData, class: 'link long' }, svg);
      svgEl('title', {}, path).textContent =
        'Long path: ' + (link.dir_a || 'one-way') + ' / ' + (link.dir_b || 'one-way');
      const label = svgEl(
        'text',
        { x: (fromCenter.x + toCenter.x) / 2, y: low - 4, class: 'linklabel' },
        svg,
      );
      label.textContent = 'long path';
    } else
      svgEl(
        'line',
        { x1: fromCenter.x, y1: fromCenter.y, x2: toCenter.x, y2: toCenter.y, class: 'link' },
        svg,
      );
  }
  const reach = {};
  for (const direction of exits) {
    const dest = map.exits[direction];
    if (!(dest in reach)) reach[dest] = direction;
  }
  for (const room of map.rooms) {
    const position = pos[room.id],
      dir = reach[room.id];
    const cls = [
      'room',
      room.visited ? 'visited' : '',
      room.explored ? '' : 'unexplored',
      room.current ? 'current' : '',
      dir && !room.current ? 'reachable' : '',
    ]
      .filter(Boolean)
      .join(' ');
    const group = svgEl('g', { class: cls }, svg);
    if (room.current)
      svgEl(
        'rect',
        {
          x: position.x - 4,
          y: position.y - 4,
          width: CW + 8,
          height: CH + 8,
          rx: 14,
          class: 'you-ring',
        },
        group,
      );
    svgEl('rect', { x: position.x, y: position.y, width: CW, height: CH, rx: 11 }, group);
    const tag = room.current ? 'You are here' : dir ? dir[0].toUpperCase() + dir.slice(1) : '';
    const lines = wrapName((room.explored ? '' : '? ') + room.name);
    let textY = tag
      ? position.y + (lines.length > 1 ? 30 : 36)
      : position.y + (lines.length > 1 ? 24 : CH / 2 + 5);
    if (tag) {
      const tagLabel = svgEl(
        'text',
        { x: position.x + CW / 2, y: position.y + 15, class: 'tag' },
        group,
      );
      tagLabel.textContent = tag;
    }
    for (const line of lines) {
      const nameLabel = svgEl('text', { x: position.x + CW / 2, y: textY }, group);
      nameLabel.textContent = line;
      textY += 15;
    }
    svgEl('title', {}, group).textContent =
      room.name +
      (room.current ? ' (you are here)' : dir ? '. Click to move ' + dir + '.' : '') +
      (room.visited ? ' Visited.' : '');
    if (dir && !room.current) {
      group.setAttribute('tabindex', '0');
      group.setAttribute('role', 'button');
      const go = () => send('MOVE ' + dir);
      group.addEventListener('click', go);
      group.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          go();
        }
      });
    }
  }
  view.appendChild(svg);
  // Keep the current room visible when the map is wider than the panel (mobile).
  const cur = map.rooms.find((room) => room.current);
  if (cur && view.scrollWidth > view.clientWidth)
    view.scrollLeft = Math.max(
      0,
      ((pos[cur.id].x + CW / 2) / width) * view.scrollWidth - view.clientWidth / 2,
    );
}

function renderInventory(ids) {
  window.Scene?.inventory(ids);
}

function renderJournal(list) {
  const el = byId('journal');
  el.replaceChildren();
  if (!list.length) {
    el.innerHTML =
      '<span class="empty">No quests yet. TALK to the Master Cartographer in Clockwork Square to begin.</span>';
    return;
  }
  const sorted = [...list].sort(
    (first, second) => (first.status === 'completed') - (second.status === 'completed'),
  );
  for (const quest of sorted) {
    const card = document.createElement('div');
    card.className = 'quest ' + (quest.status || '') + (quest.final ? ' final' : '');
    const st = document.createElement('span');
    st.className = 'state';
    st.textContent = quest.status + (quest.progress ? ' ' + quest.progress : '');
    const name = document.createElement('b');
    name.textContent = (quest.name || quest.quest_id) + (quest.final ? ' (final quest)' : '');
    card.append(st, name);
    if (quest.description && quest.status !== 'completed') {
      const paragraph = document.createElement('p');
      paragraph.textContent = quest.description;
      card.appendChild(paragraph);
    }
    el.appendChild(card);
  }
}

function showVictory() {
  const panel = byId('victoryPanel');
  if (catalog.story?.victory) byId('victoryText').textContent = catalog.story.victory;
  panel.classList.remove('hide');
}

function refresh() {
  if (!sessionID || !active) return Promise.resolve();
  for (const cmd of ['LOOK', 'INVENTORY', 'STATUS', 'WHO', 'QUESTS']) send(cmd, true);
  return Promise.resolve();
}

async function disconnect(sendQuit = true) {
  const id = sessionID;
  if (!id) return;
  if (sendQuit) {
    await send('QUIT');
    setTimeout(() => {
      if (sessionID === id) disconnect(false);
    }, 1500);
    return;
  } // wait for "OK bye" and its narration
  if (stream) {
    stream.close();
    stream = null;
  }
  sessionID = '';
  commandQueue = [];
  setOnline(false);
  try {
    await api('/api/close', { id });
  } catch {}
}

function updateSkin() {
  const name = byId('username').value.trim();
  if (window.Scene) byId('skinPreview').innerHTML = name ? Scene.heroSprite(name) : '';
  const sk = name && window.Scene ? Scene.skinFor(name) : null;
  byId('skinNote').textContent = sk
    ? 'You will be a ' +
      sk.species +
      '. Your character comes from your name, so everyone sees you the same way.'
    : 'Your character (cat or rabbit) comes from your name, so everyone sees you the same way.';
}
on('username', 'input', updateSkin);
on('connectForm', 'submit', (event) => {
  event.preventDefault();
  connect(byId('username').value.trim());
});
for (const button of document.querySelectorAll('[data-action]'))
  button.addEventListener('click', () => send(button.dataset.action));
on('quitBtn', 'click', () => disconnect());
on('clearLog', 'click', () => byId('protocolLog').replaceChildren());
on('rawForm', 'submit', (event) => {
  event.preventDefault();
  const line = byId('rawCommand').value.trim();
  if (line) send(line);
  byId('rawCommand').value = '';
});
on('chatForm', 'submit', (event) => {
  event.preventDefault();
  const txt = byId('chatMessage').value.trim();
  if (txt) send('CHAT ' + chatTarget() + ' ' + txt);
  byId('chatMessage').value = '';
});
for (const tab of byId('chatTabs').querySelectorAll('button'))
  tab.addEventListener('click', () => {
    scope = tab.dataset.scope;
    renderChat();
  });
window.addEventListener('beforeunload', () => {
  if (sessionID)
    navigator.sendBeacon(
      '/api/close',
      new Blob([JSON.stringify({ id: sessionID })], { type: 'application/json' }),
    );
});
fetch('/api/catalog')
  .then((response) => (response.ok ? response.json() : {}))
  .then((data) => {
    catalog = data;
    if (data.story?.title)
      byId('storyTitle').textContent =
        data.story.title + ', a shared-world adventure over RFC 42TAP';
  })
  .catch(() => {});
setInterval(() => {
  if (active && sessionID && commandQueue.length < 10) {
    send('LOOK', true);
    send('WHO', true);
  }
}, 10000);
