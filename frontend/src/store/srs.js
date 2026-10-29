// Логика интервального повторения карточек.
//
// 1. Основной проход: все слова темы по одному разу (в случайном порядке).
//    «Учить ещё раз» откладывает слово в блок повторения.
// 2. Блок повторения (в конце): только отложенные слова. Если слово снова
//    «Учить ещё раз», оно возвращается в очередь не сразу, а через
//    REPEAT_GAP карточек (8–12), чтобы не мелькало каждые 5–7 слов.
//    Если в очереди меньше карточек — слово уходит в конец.
// 3. Режим «Повторение» (все пройденные темы): колоду собирает бэкенд
//    (backend/learning/services.py → build_review_deck) — слова выбираются
//    с весом, трудные попадаются заметно чаще.

export const REPEAT_GAP = { min: 8, max: 12 }

export function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export function reinsert(queue, word) {
  const gap = REPEAT_GAP.min + Math.floor(Math.random() * (REPEAT_GAP.max - REPEAT_GAP.min + 1))
  const q = [...queue]
  q.splice(Math.min(gap, q.length), 0, word)
  return q
}

// Так же, как is_hard в backend/learning/services.py
export const isHard = (stat) => !!stat && stat.again >= 2 && stat.again >= stat.learned
