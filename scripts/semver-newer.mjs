#!/usr/bin/env node
// 두 semver 를 비교해 두 번째가 첫 번째보다 새 버전이면 "true", 아니면 "false" 를 출력한다.
// 프리릴리즈는 같은 번호의 정식보다 낮다: 2.17.0-dev.1 < 2.17.0.
// 사용법: node scripts/semver-newer.mjs <current> <candidate>     (앞의 v 는 무시)

function parse(input) {
  const match = String(input).trim().replace(/^v/, '').match(/^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?/);
  if (!match) throw new Error(`semver 가 아니다: ${input}`);
  return {
    core: [Number(match[1]), Number(match[2]), Number(match[3])],
    pre: match[4] ? match[4].split('.') : null,
  };
}

function compareIdentifiers(left, right) {
  const leftNumeric = /^\d+$/.test(left);
  const rightNumeric = /^\d+$/.test(right);
  if (leftNumeric && rightNumeric) return Math.sign(Number(left) - Number(right));
  if (leftNumeric) return -1;          // 숫자 식별자는 문자 식별자보다 낮다
  if (rightNumeric) return 1;
  return left < right ? -1 : left > right ? 1 : 0;
}

export function compareSemver(a, b) {
  const left = parse(a);
  const right = parse(b);
  for (let i = 0; i < 3; i += 1) {
    if (left.core[i] !== right.core[i]) return Math.sign(left.core[i] - right.core[i]);
  }
  if (!left.pre && !right.pre) return 0;
  if (!left.pre) return 1;             // 정식 > 프리릴리즈
  if (!right.pre) return -1;
  const length = Math.max(left.pre.length, right.pre.length);
  for (let i = 0; i < length; i += 1) {
    if (left.pre[i] === undefined) return -1;
    if (right.pre[i] === undefined) return 1;
    const order = compareIdentifiers(left.pre[i], right.pre[i]);
    if (order !== 0) return order;
  }
  return 0;
}

const [, , current, candidate] = process.argv;
if (current !== undefined || candidate !== undefined) {
  if (!current || !candidate) {
    console.error('사용법: node scripts/semver-newer.mjs <current> <candidate>');
    process.exit(2);
  }
  try {
    process.stdout.write(compareSemver(current, candidate) < 0 ? 'true\n' : 'false\n');
  } catch (error) {
    console.error(error.message);
    process.exit(2);
  }
}
