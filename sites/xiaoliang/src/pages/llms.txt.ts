// Plain-text profile summary for LLM crawlers (https://llmstxt.org/).
import type { APIRoute } from 'astro';
import { homeUrl, homeUrlZh, profile as p } from '../lib/profile';

export const GET: APIRoute = () => {
  const native = p.zh.name_native ?? '';
  const lines = [
    `# ${p.name}`,
    '',
    `> ${p.description.trim()}`,
    '',
    '## Canonical profile',
    `- Homepage: ${homeUrl}`,
    `- Chinese version (简体中文): ${homeUrlZh}`,
    '',
    '## Names',
    '- English name: Xiao Liang',
    `- Chinese name: ${native} (pinyin: Liang Xiao in Chinese order; Xiao Liang in English order)`,
    '',
    '## Academic identity',
    '- Ph.D. student, Department of Electrical and Computer Engineering, Iowa State University (2024 - present)',
    `- Advisor: ${p.advisor} (${p.advisor_link})`,
    ...p.links.map((l) => `- ${l.label}: ${l.url}`),
    '',
    '## Disambiguation',
    `This profile is for Xiao Liang (${native}) at Iowa State University (ECE), who works on nonconvex optimization, tensor recovery, and signal processing. It is not the Xiao Liang at UCLA who works on large language models.`,
    '',
    '## Research topics',
    ...p.interests.map((i) => `- ${i.replaceAll('&amp;', '&')}`),
    '',
    '## Selected publications',
    ...p.research.map((pub) => {
      const authors = pub.authors.replace(/<[^>]*>/g, '').replaceAll('&dagger;', '').replaceAll('*', '');
      return `- ${pub.title}. ${authors}. ${pub.venue}. ${pub.links[0]!.url}`;
    }),
    '',
    '## Experience',
    '- Intern, Huawei (before starting the Ph.D.)',
    '',
    '## Education',
    ...p.education.map((e) => `- ${e.degree}, ${e.school} (${e.years.replaceAll('&ndash;', '-')})`),
  ];
  return new Response(lines.join('\n') + '\n', { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
