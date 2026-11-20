// Compare the word sequence of the specification page on docs.nemar.org with spec/index.md.
//
// The text moved with no normative change, so the two files must differ only in markup:
// the Starlight front matter and asides, link targets, emphasis, and table and list syntax.
// This script strips that markup from both files and prints the number of differing words.
//
// Usage: bun run tools/check-moved-text.ts [source.md [moved.md]]
//
// With no source argument, the source is read from the default branch of nemarOrg/docs
// through the GitHub CLI (`gh`), which needs read access to that repository.

const SOURCE_REPO_PATH = "repos/nemarOrg/docs/contents/src/content/docs/formats/biosig-zarr.md";
const MOVED_DEFAULT = new URL("../spec/index.md", import.meta.url).pathname;

/** Turn a Starlight page into plain Markdown: front matter to a title heading, asides to labels. */
export function stripStarlight(text: string): string {
  const lines = text.split("\n");
  let body = lines;
  let heading = "";
  if (lines[0] === "---") {
    const end = lines.indexOf("---", 1);
    const title = lines.slice(1, end).find((line) => line.startsWith("title:"));
    heading = title ? `# ${title.slice("title:".length).trim().replace(/^"|"$/g, "")}` : "";
    body = lines.slice(end + 1);
  }
  const out: string[] = heading ? [heading] : [];
  for (const line of body) {
    const aside = line.match(/^:::(\w+)\[(.*)\]\s*$/);
    if (aside) out.push(`${aside[1]} ${aside[2]}`);
    else if (line.trim() !== ":::") out.push(line);
  }
  return out.join("\n");
}

/** Turn a moved aside label, `> **Note. Title.**`, back into the words `note Title`. */
function foldAsideLabel(line: string): string {
  const label = line.match(/^>\s*\*\*(\w+)\. (.*)\.\*\*\s*$/);
  return label ? `${label[1].toLowerCase()} ${label[2]}` : line;
}

/** Strip Markdown markup from one line and return it as plain text. */
function stripMarkup(line: string): string {
  let text = foldAsideLabel(line);
  if (/^\|?[\s:|-]+\|?$/.test(text) && text.includes("-")) return "";
  text = text.replace(/^\s*>+\s?/, "");
  text = text.replace(/^\s*#{1,6}\s+/, "");
  text = text.replace(/^\s*[-*]\s+/, "");
  text = text.replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1");
  text = text.replace(/\*\*|`|\|/g, " ");
  return text;
}

/** The ordered list of whitespace-separated words left after stripping the markup. */
export function words(markdown: string): string[] {
  return markdown
    .split("\n")
    .filter((line) => !/^```/.test(line.trim()))
    .flatMap((line) => stripMarkup(line).split(/\s+/))
    .filter((word) => word.length > 0);
}

/** The number of words that differ between two sequences, and the first differing context. */
export function diffWords(a: string[], b: string[]): { count: number; context: string } {
  let start = 0;
  while (start < a.length && start < b.length && a[start] === b[start]) start++;
  let endA = a.length;
  let endB = b.length;
  while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) {
    endA--;
    endB--;
  }
  const midA = a.slice(start, endA);
  const midB = b.slice(start, endB);
  if (midA.length === 0 && midB.length === 0) return { count: 0, context: "" };
  const context = `at word ${start}: source "${midA.slice(0, 8).join(" ")}" vs moved "${midB.slice(0, 8).join(" ")}"`;
  if (midA.length * midB.length > 5e7) return { count: midA.length + midB.length, context };
  // Longest common subsequence of the differing middle, with a rolling row.
  let prev = new Array<number>(midB.length + 1).fill(0);
  for (let i = 1; i <= midA.length; i++) {
    const row = new Array<number>(midB.length + 1).fill(0);
    for (let j = 1; j <= midB.length; j++) {
      row[j] = midA[i - 1] === midB[j - 1] ? prev[j - 1] + 1 : Math.max(prev[j], row[j - 1]);
    }
    prev = row;
  }
  const common = prev[midB.length];
  return { count: midA.length - common + (midB.length - common), context };
}

async function readSource(path: string | undefined): Promise<string> {
  if (path) return Bun.file(path).text();
  const run = Bun.spawn(
    ["gh", "api", "-H", "Accept: application/vnd.github.raw", SOURCE_REPO_PATH],
    {
      stdout: "pipe",
      stderr: "pipe",
    },
  );
  const [out, err] = await Promise.all([
    new Response(run.stdout).text(),
    new Response(run.stderr).text(),
  ]);
  if ((await run.exited) !== 0) {
    throw new Error(`could not read the source through gh: ${err.trim()}`);
  }
  return out;
}

if (import.meta.main) {
  const [sourcePath, movedPath] = Bun.argv.slice(2);
  const source = words(stripStarlight(await readSource(sourcePath)));
  const moved = words(await Bun.file(movedPath ?? MOVED_DEFAULT).text());
  const { count, context } = diffWords(source, moved);
  console.log(`${source.length} source words, ${moved.length} moved words`);
  console.log(`${count} differing words`);
  if (count > 0) {
    console.log(context);
    process.exit(1);
  }
}
