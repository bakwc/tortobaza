function fold(value: string): string {
  return value.toLowerCase().replaceAll("ё", "е");
}

function words(value: string): string[] {
  const folded = fold(value).trim();
  if (folded === "") return [];
  return folded.split(/\s+/);
}

type NameScore = { extra: number; penalty: number; length: number };

function score(label: string, query: string): NameScore | null {
  const tokens = words(query);
  if (tokens.length === 0) return { extra: 0, penalty: 0, length: 0 };
  const nameWords = words(label);
  const order = tokens
    .map((token, index) => ({ token, index }))
    .sort((left, right) => right.token.length - left.token.length || left.index - right.index);
  const used = nameWords.map(() => false);
  let penalty = 0;
  for (const { token } of order) {
    let best = -1;
    for (let index = 0; index < nameWords.length; index += 1) {
      if (used[index]) continue;
      const word = nameWords[index];
      if (!word.startsWith(token)) continue;
      if (best === -1 || word.length < nameWords[best].length) best = index;
    }
    if (best === -1) return null;
    used[best] = true;
    penalty += nameWords[best].length - token.length;
  }
  return { extra: used.filter((flag) => !flag).length, penalty, length: fold(label).length };
}

export function nameMatches(label: string, query: string): boolean {
  return score(label, query) !== null;
}

export function compareNameMatch(left: string, right: string, query: string): number {
  if (words(query).length === 0) return 0;
  const leftScore = score(left, query);
  const rightScore = score(right, query);
  if (leftScore === null && rightScore === null) return 0;
  if (leftScore === null) return 1;
  if (rightScore === null) return -1;
  if (leftScore.extra !== rightScore.extra) return leftScore.extra - rightScore.extra;
  if (leftScore.penalty !== rightScore.penalty) return leftScore.penalty - rightScore.penalty;
  return leftScore.length - rightScore.length;
}

export function namesEqual(left: string, right: string): boolean {
  return fold(left).trim() === fold(right).trim();
}
