// Quiz Me: flashcards and quizzes over decks in ./decks/*.json.
// Progress lives in localStorage, one key per deck.

const STORE_PREFIX = 'quiz-me:';
const ROUND_SIZE = 20;
const QUIZ_LENGTH = 10;
const REQUEUE_GAP = 4;
const MAX_MISSES_PER_ROUND = 2;
const BOX_NAMES = ['New', 'Learning', 'Familiar', 'Strong', 'Known'];
const KNOWN_BOX = BOX_NAMES.length - 1;
const CHOICE_KEYS = ['A', 'B', 'C', 'D', 'E', 'F'];

const app = document.getElementById('app');
const live = document.getElementById('live');
const decks = loadDecks();
let session = null;

// ---------- decks ----------

function loadDecks() {
	const modules = import.meta.glob('./decks/*.json', { eager: true, import: 'default' });
	return Object.entries(modules)
		.map(([path, data]) => normaliseDeck(path, data))
		.sort((a, b) => a.title.localeCompare(b.title));
}

function normaliseDeck(path, data) {
	const slug = path.split('/').pop().replace(/\.json$/, '');
	const cards = (data.cards || []).map((card) => ({ ...card, id: card.id || 'c' + hash(card.front) }));
	const questions = (data.questions || []).map((q) => ({ ...q, id: q.id || 'q' + hash(q.ask) }));
	const topics = data.topics && data.topics.length ? data.topics : uniqueTopics([...cards, ...questions]);
	return {
		slug,
		title: data.title || slug,
		about: data.about || '',
		source: data.source || '',
		created: data.created || '',
		topics,
		cards,
		questions,
	};
}

function uniqueTopics(items) {
	return [...new Set(items.map((item) => item.topic).filter(Boolean))];
}

function findDeck(slug) {
	return decks.find((deck) => deck.slug === slug);
}

function byTopic(items, topic) {
	if (topic === 'all') return items;
	return items.filter((item) => item.topic === topic);
}

// ---------- progress ----------

function readProgress(slug) {
	try {
		const saved = JSON.parse(localStorage.getItem(STORE_PREFIX + slug));
		return { cards: {}, quizzes: [], ...saved };
	} catch {
		return { cards: {}, quizzes: [] };
	}
}

function writeProgress(slug, progress) {
	try {
		localStorage.setItem(STORE_PREFIX + slug, JSON.stringify(progress));
	} catch {
		// Storage can be blocked (private windows). The session still works.
	}
}

function clearProgress(slug) {
	try {
		localStorage.removeItem(STORE_PREFIX + slug);
	} catch {
		// Nothing to clear.
	}
}

function boxOf(progress, card) {
	const record = progress.cards[card.id];
	return record ? record.box : 0;
}

function lastSeenOf(progress, card) {
	const record = progress.cards[card.id];
	return record ? record.seen : 0;
}

function boxCounts(progress, cards) {
	const counts = BOX_NAMES.map(() => 0);
	cards.forEach((card) => { counts[boxOf(progress, card)] += 1; });
	return counts;
}

function recordCard(slug, card, gotIt) {
	const progress = readProgress(slug);
	// A new card you get right counts as Learning, then moves up one.
	const box = gotIt ? Math.min(Math.max(boxOf(progress, card), 1) + 1, KNOWN_BOX) : 1;
	progress.cards[card.id] = { box, seen: Date.now() };
	writeProgress(slug, progress);
}

function recordQuiz(slug, topic, score, total) {
	const progress = readProgress(slug);
	progress.quizzes = [...progress.quizzes, { at: Date.now(), topic, score, total }].slice(-20);
	writeProgress(slug, progress);
}

// ---------- routing ----------

function parseRoute() {
	const [slug = '', mode = 'cards', topic = 'all'] = location.hash.replace(/^#\/?/, '').split('/').map(decodeURIComponent);
	return { slug, mode: mode === 'quiz' ? 'quiz' : 'cards', topic };
}

function routeTo(slug, mode, topic) {
	return '#/' + [slug, mode, topic].map(encodeURIComponent).join('/');
}

function sessionKey(route) {
	return [route.slug, route.mode, route.topic].join('/');
}

// ---------- sessions ----------

function startCardRound(deck, topic) {
	const progress = readProgress(deck.slug);
	const queue = shuffle(byTopic(deck.cards, topic))
		.sort((a, b) => boxOf(progress, a) - boxOf(progress, b) || lastSeenOf(progress, a) - lastSeenOf(progress, b))
		.slice(0, ROUND_SIZE);
	return { kind: 'cards', queue, index: 0, flipped: false, got: 0, missed: 0, misses: {} };
}

function startQuiz(deck, topic) {
	const items = shuffle(byTopic(deck.questions, topic))
		.slice(0, QUIZ_LENGTH)
		.map((q) => ({ q, order: shuffle(q.choices.map((_, i) => i)), picked: null }));
	return { kind: 'quiz', items, index: 0, score: 0, saved: false };
}

function ensureSession(deck, route) {
	const key = sessionKey(route);
	if (session && session.key === key) return session;
	const fresh = route.mode === 'quiz' ? startQuiz(deck, route.topic) : startCardRound(deck, route.topic);
	session = { ...fresh, key };
	return session;
}

// ---------- rendering: shell ----------

function render() {
	const route = parseRoute();
	const deck = findDeck(route.slug) || (decks.length === 1 ? decks[0] : null);
	if (!decks.length) return renderEmpty();
	if (!deck) return renderCatalog();
	if (route.topic !== 'all' && !deck.topics.includes(route.topic)) route.topic = 'all';
	route.slug = deck.slug;
	ensureSession(deck, route);
	app.innerHTML = `
		<div class="sheet">
			${deckHeader(deck, route)}
			<section class="stage" aria-label="${route.mode === 'quiz' ? 'Quiz' : 'Flashcards'}">
				${topicTabs(deck, route)}
				<div class="stage-body">${stageBody(deck, route)}</div>
			</section>
			${route.mode === 'quiz' ? quizFooter(deck) : cardFooter(deck, route.topic)}
		</div>`;
	document.title = deck.title + ' | Quiz Me';
}

function renderEmpty() {
	app.innerHTML = `
		<div class="sheet">
			<header class="deck-head"><h1>Quiz Me</h1></header>
			<div class="card-wrap" data-pile="0">
				<article class="card"><div class="face front">
					<div class="card-head"><span class="card-topic">Empty</span></div>
					<div class="card-text"><p>No decks yet.</p><p>Ask Claude to quiz you on this project, then refresh this page.</p></div>
				</div></article>
			</div>
		</div>`;
}

function renderCatalog() {
	const items = decks.map((deck) => catalogItem(deck)).join('');
	app.innerHTML = `
		<div class="sheet">
			<header class="deck-head">
				<h1>Quiz Me</h1>
				<p class="about">Pick a deck to study.</p>
			</header>
			<ul class="catalog">${items}</ul>
		</div>`;
	document.title = 'Quiz Me';
}

function catalogItem(deck) {
	const progress = readProgress(deck.slug);
	const known = boxCounts(progress, deck.cards)[KNOWN_BOX];
	return `
		<li class="divider">
			<a class="divider-tab" href="${routeTo(deck.slug, 'cards', 'all')}">${escapeHtml(deck.title)}</a>
			<div class="divider-body">
				<p>${escapeHtml(deck.about)}</p>
				<p class="divider-meta">${plural(deck.cards.length, 'card')}, ${plural(deck.questions.length, 'question')}. ${known} known.</p>
			</div>
		</li>`;
}

function deckHeader(deck, route) {
	const back = decks.length > 1 ? '<a class="back" href="#/">All decks</a>' : '';
	const source = [deck.source, deck.created].filter(Boolean).map(escapeHtml).join(', ');
	return `
		<header class="deck-head">
			${back}
			<h1>${escapeHtml(deck.title)}</h1>
			${deck.about ? `<p class="about">${escapeHtml(deck.about)}</p>` : ''}
			${source ? `<p class="source">${source}</p>` : ''}
			<nav class="modes" aria-label="Mode">
				${modeLink(deck, route, 'cards', 'Flashcards', deck.cards.length)}
				${modeLink(deck, route, 'quiz', 'Quiz', deck.questions.length)}
			</nav>
		</header>`;
}

function modeLink(deck, route, mode, label, count) {
	const current = route.mode === mode ? ' aria-current="page"' : '';
	return `<a href="${routeTo(deck.slug, mode, route.topic)}"${current}>${label} <span class="count">${count}</span></a>`;
}

function topicTabs(deck, route) {
	if (deck.topics.length < 2) return '';
	const tabs = ['all', ...deck.topics].map((topic) => {
		const current = route.topic === topic ? ' aria-current="true"' : '';
		const label = topic === 'all' ? 'All topics' : topic;
		return `<a class="tab" href="${routeTo(deck.slug, route.mode, topic)}"${current}>${escapeHtml(label)}</a>`;
	});
	return `<nav class="tabs" aria-label="Topics">${tabs.join('')}</nav>`;
}

function stageBody(deck, route) {
	if (route.mode === 'quiz') return quizStage(deck);
	return cardStage(deck);
}

// ---------- rendering: flashcards ----------

function cardStage(deck) {
	const card = session.queue[session.index];
	if (!session.queue.length) return blankCard('Nothing here', 'No flashcards for this topic yet.');
	if (!card) return roundSummary(deck);
	const remaining = session.queue.length - session.index - 1;
	return `
		<div class="card-wrap" data-pile="${Math.min(remaining, 2)}">
			<article class="card${session.flipped ? ' is-flipped' : ''}" data-action="flip">
				<div class="face front"${session.flipped ? ' inert' : ''}>
					<div class="card-head">
						<span class="card-topic">${escapeHtml(card.topic || '')}</span>
						<span class="card-count">${session.index + 1} of ${session.queue.length}</span>
					</div>
					<div class="card-text">${rich(card.front)}</div>
				</div>
				<div class="face back"${session.flipped ? '' : ' inert'}>
					<div class="card-text">${rich(card.back)}</div>
					${refLine(card.ref)}
				</div>
			</article>
		</div>
		<div class="actions">${cardActions()}</div>`;
}

function cardActions() {
	if (!session.flipped) {
		return `<button type="button" class="btn btn-primary" data-action="flip">Show answer <kbd>Space</kbd></button>`;
	}
	return `
		<button type="button" class="btn" data-action="missed">Missed it <kbd>1</kbd></button>
		<button type="button" class="btn btn-primary" data-action="got">Got it <kbd>2</kbd></button>`;
}

function roundSummary(deck) {
	const progress = readProgress(deck.slug);
	const known = boxCounts(progress, deck.cards)[KNOWN_BOX];
	return `
		<div class="card-wrap" data-pile="0">
			<article class="card"><div class="face front">
				<div class="card-head"><span class="card-topic">Round done</span></div>
				<div class="card-text">
					<p class="pen-mark">${session.got} got, ${session.missed} missed</p>
					<p>${known} of ${deck.cards.length} cards are known. Weakest cards come first next round.</p>
				</div>
			</div></article>
		</div>
		<div class="actions">
			<button type="button" class="btn btn-primary" data-action="next-round">Next round <kbd>Enter</kbd></button>
		</div>`;
}

function cardFooter(deck, topic) {
	const cards = byTopic(deck.cards, topic);
	const counts = boxCounts(readProgress(deck.slug), cards);
	const cells = counts.map((count, i) => `
		<li><span class="box-count">${count}</span><span class="box-name">${BOX_NAMES[i]}</span></li>`).join('');
	return `
		<footer class="progress">
			<h2 class="progress-title">Your progress</h2>
			<ol class="boxes">${cells}</ol>
			<p class="progress-note">A card moves right each time you get it, and back to Learning when you miss it.</p>
			<button type="button" class="link-btn" data-action="reset">Reset progress</button>
		</footer>`;
}

// ---------- rendering: quiz ----------

function quizStage(deck) {
	const item = session.items[session.index];
	if (!session.items.length) return blankCard('Nothing here', 'No quiz questions for this topic yet.');
	if (!item) return quizSummary(deck);
	return `
		<div class="card-wrap" data-pile="${Math.min(session.items.length - session.index - 1, 2)}">
			<article class="card quiz-card"><div class="face front">
				<div class="card-head">
					<span class="card-topic">${escapeHtml(item.q.topic || '')}</span>
					<span class="card-count">${session.index + 1} of ${session.items.length}</span>
				</div>
				<div class="card-text">${rich(item.q.ask)}</div>
				<ol class="choices">${item.order.map((choiceIndex, slot) => choiceButton(item, choiceIndex, slot)).join('')}</ol>
				${item.picked === null ? '' : verdict(item)}
			</div></article>
		</div>
		<div class="actions">${item.picked === null ? '' : nextButton()}</div>`;
}

function choiceButton(item, choiceIndex, slot) {
	const answered = item.picked !== null;
	const isAnswer = answered && choiceIndex === item.q.answer;
	const isWrongPick = answered && choiceIndex === item.picked && !isAnswer;
	const classes = ['choice', isAnswer ? 'is-answer' : '', isWrongPick ? 'is-wrong' : ''].filter(Boolean).join(' ');
	const note = isAnswer ? '<span class="sr-only"> (correct answer)</span>' : isWrongPick ? '<span class="sr-only"> (your pick)</span>' : '';
	const disabled = answered ? ' aria-disabled="true"' : '';
	return `
		<li><button type="button" class="${classes}" data-action="pick" data-choice="${choiceIndex}"${disabled}>
			<span class="choice-key">${CHOICE_KEYS[slot]}.</span>
			<span class="choice-text">${richInline(item.q.choices[choiceIndex])}</span>${note}
		</button></li>`;
}

function verdict(item) {
	const right = item.picked === item.q.answer;
	return `
		<div class="verdict">
			<p class="pen-mark">${right ? 'Right.' : 'Not quite.'}</p>
			<div class="why">${rich(item.q.why || '')}</div>
			${refLine(item.q.ref)}
		</div>`;
}

function nextButton() {
	const last = session.index === session.items.length - 1;
	return `<button type="button" class="btn btn-primary" data-action="next">${last ? 'See score' : 'Next question'} <kbd>Enter</kbd></button>`;
}

function quizSummary(deck) {
	saveQuizOnce(deck);
	const misses = session.items.filter((item) => item.picked !== item.q.answer);
	const list = misses.map((item) => `
		<li><div class="miss-ask">${rich(item.q.ask)}</div>
		<p class="miss-answer">Answer: ${richInline(item.q.choices[item.q.answer])}</p></li>`).join('');
	return `
		<div class="card-wrap" data-pile="0">
			<article class="card"><div class="face front">
				<div class="card-head"><span class="card-topic">Score</span></div>
				<div class="card-text">
					<p class="score"><span>${session.score}</span> / ${session.items.length}</p>
					${misses.length ? `<p>Worth another look:</p><ol class="misses">${list}</ol>` : '<p>Clean sheet.</p>'}
				</div>
			</div></article>
		</div>
		<div class="actions">
			<button type="button" class="btn btn-primary" data-action="new-quiz">New quiz <kbd>Enter</kbd></button>
		</div>`;
}

function saveQuizOnce(deck) {
	if (session.saved) return;
	session.saved = true;
	recordQuiz(deck.slug, parseRoute().topic, session.score, session.items.length);
}

function quizFooter(deck) {
	const quizzes = readProgress(deck.slug).quizzes.slice(-6).reverse();
	const scores = quizzes.map((quiz) => `<li>${quiz.score}/${quiz.total}<span class="sr-only"> on ${escapeHtml(quiz.topic === 'all' ? 'all topics' : quiz.topic)}</span></li>`).join('');
	return `
		<footer class="progress">
			<h2 class="progress-title">Recent scores</h2>
			${scores ? `<ol class="scores">${scores}</ol>` : '<p class="progress-note">No quizzes taken yet.</p>'}
			<button type="button" class="link-btn" data-action="reset">Reset progress</button>
		</footer>`;
}

// ---------- rendering: shared bits ----------

function blankCard(head, text) {
	return `
		<div class="card-wrap" data-pile="0">
			<article class="card"><div class="face front">
				<div class="card-head"><span class="card-topic">${escapeHtml(head)}</span></div>
				<div class="card-text"><p>${escapeHtml(text)}</p></div>
			</div></article>
		</div>`;
}

function refLine(ref) {
	if (!ref) return '';
	return `<p class="card-ref">from <code>${escapeHtml(ref)}</code></p>`;
}

// ---------- actions ----------

const actions = {
	flip: flipCard,
	got: () => answerCard(true),
	missed: () => answerCard(false),
	'next-round': restartSession,
	pick: pickChoice,
	next: nextQuestion,
	'new-quiz': restartSession,
	reset: resetProgress,
};

function flipCard() {
	session.flipped = !session.flipped;
	const card = app.querySelector('.card');
	card.classList.toggle('is-flipped', session.flipped);
	card.querySelector('.front').inert = session.flipped;
	card.querySelector('.back').inert = !session.flipped;
	app.querySelector('.actions').innerHTML = cardActions();
	if (session.flipped) announce('Answer: ' + card.querySelector('.back').textContent);
}

function answerCard(gotIt) {
	if (!session.flipped) return;
	const deck = findDeck(parseRoute().slug) || decks[0];
	const card = session.queue[session.index];
	recordCard(deck.slug, card, gotIt);
	if (gotIt) session.got += 1;
	if (!gotIt) requeueMissed(card);
	session.index += 1;
	session.flipped = false;
	render();
}

function requeueMissed(card) {
	session.missed += 1;
	const misses = (session.misses[card.id] || 0) + 1;
	session.misses[card.id] = misses;
	if (misses > MAX_MISSES_PER_ROUND) return;
	const at = Math.min(session.index + 1 + REQUEUE_GAP, session.queue.length);
	session.queue.splice(at, 0, card);
}

function pickChoice(target) {
	const item = session.items[session.index];
	if (!item || item.picked !== null) return;
	item.picked = Number(target.dataset.choice);
	if (item.picked === item.q.answer) session.score += 1;
	render();
	announce((item.picked === item.q.answer ? 'Right. ' : 'Not quite. ') + (item.q.why || ''));
}

function pickSlot(slot) {
	const item = session.items[session.index];
	if (!item || slot >= item.order.length) return;
	pickChoice({ dataset: { choice: item.order[slot] } });
}

function nextQuestion() {
	const item = session.items[session.index];
	if (!item || item.picked === null) return;
	session.index += 1;
	render();
}

function restartSession() {
	session = null;
	render();
}

function resetProgress() {
	const deck = findDeck(parseRoute().slug) || decks[0];
	if (!confirm(`Reset all progress for "${deck.title}"?`)) return;
	clearProgress(deck.slug);
	restartSession();
}

app.addEventListener('click', (event) => {
	const target = event.target.closest('[data-action]');
	if (!target || target.getAttribute('aria-disabled') === 'true') return;
	actions[target.dataset.action](target);
});

// ---------- keyboard ----------

document.addEventListener('keydown', (event) => {
	if (event.metaKey || event.ctrlKey || event.altKey) return;
	if (!session || !app.querySelector('.stage')) return;
	const onControl = event.target.closest && event.target.closest('button, a');
	if (onControl && (event.key === ' ' || event.key === 'Enter')) return;
	const handled = session.kind === 'quiz' ? quizKey(event.key) : cardKey(event.key);
	if (handled) event.preventDefault();
});

function cardKey(key) {
	if (session.index >= session.queue.length) return key === 'Enter' && actionThen(restartSession);
	if (key === ' ' || key === 'Enter') return actionThen(flipCard);
	if (!session.flipped) return false;
	if (key === '1' || key === 'ArrowLeft') return actionThen(() => answerCard(false));
	if (key === '2' || key === 'ArrowRight') return actionThen(() => answerCard(true));
	return false;
}

function quizKey(key) {
	const item = session.items[session.index];
	if (!item) return key === 'Enter' && actionThen(restartSession);
	if (item.picked !== null) return (key === 'Enter' || key === ' ' || key === 'ArrowRight') && actionThen(nextQuestion);
	const letterSlot = CHOICE_KEYS.indexOf(key.toUpperCase());
	const numberSlot = Number(key) - 1;
	const slot = letterSlot >= 0 ? letterSlot : numberSlot;
	if (!Number.isInteger(slot) || slot < 0) return false;
	return actionThen(() => pickSlot(slot));
}

function actionThen(fn) {
	fn();
	return true;
}

// ---------- text ----------

function rich(text) {
	return String(text ?? '')
		.split('```')
		.map((part, i) => (i % 2 ? codeBlock(part) : paragraphs(part)))
		.join('');
}

function codeBlock(part) {
	const body = part.replace(/^[\w+#.-]*\n/, '').replace(/\n$/, '');
	return `<pre><code>${escapeHtml(body)}</code></pre>`;
}

function paragraphs(part) {
	return part
		.split(/\n\s*\n/)
		.map((para) => para.trim())
		.filter(Boolean)
		.map((para) => `<p>${richInline(para).replace(/\n/g, '<br>')}</p>`)
		.join('');
}

function richInline(text) {
	return String(text ?? '')
		.split('`')
		.map((part, i) => (i % 2 ? `<code>${escapeHtml(part)}</code>` : emphasis(escapeHtml(part))))
		.join('');
}

function emphasis(html) {
	return html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}

function escapeHtml(text) {
	return String(text ?? '')
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

// ---------- utils ----------

function shuffle(items) {
	const copy = [...items];
	for (let i = copy.length - 1; i > 0; i -= 1) {
		const j = Math.floor(Math.random() * (i + 1));
		[copy[i], copy[j]] = [copy[j], copy[i]];
	}
	return copy;
}

function hash(text) {
	let value = 5381;
	for (const char of String(text ?? '')) value = ((value << 5) + value + char.codePointAt(0)) | 0;
	return (value >>> 0).toString(36);
}

function plural(count, word) {
	return `${count} ${word}${count === 1 ? '' : 's'}`;
}

function announce(text) {
	live.textContent = '';
	requestAnimationFrame(() => { live.textContent = text; });
}

window.addEventListener('hashchange', render);
render();
