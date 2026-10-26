// Site-wide settings, interface strings, and portfolio content, validated at build time.
// A missing or misspelled field fails the build instead of leaving a blank on the page.
//
// Content strings are rendered as HTML (they may contain entities and inline tags), as on the
// original Jekyll site.
import { z } from 'astro/zod';
import { parse } from 'yaml';
import i18nRaw from '../data/i18n.yaml?raw';
import portfolioJson from '../data/portfolio.json';

export type Lang = 'en' | 'zh-Hans';
export const langs: Lang[] = ['en', 'zh-Hans'];

/** Values that were in the Jekyll _config.yml. */
export const site = {
  url: 'https://danielye.net',
  author: 'Daniel Ye',
  title: 'Daniel Ye',
  description:
    'Daniel Ye (Yifei Ye, 叶逸飞) is a Ph.D. candidate in Industrial Engineering at Iowa State University, researching computational geometry, 3D deformation modeling, predictive compensation, and additive manufacturing.',
  keywords:
    'Daniel Ye, Yifei Ye, 叶逸飞, Industrial Engineering, Iowa State University, additive manufacturing, computational geometry, 3D deformation modeling, predictive compensation, digital manufacturing',
  avatar: '/assets/img/danielavatar.jpg',
  favicon: '/assets/img/favicon_black.png',
  faviconDark: '/assets/img/favicon_black.png',
  email: 'danielye0010 AT gmail DOT com',
  emailUser: 'danielye0010',
  emailDomain: 'gmail.com',
  affiliationLink: 'https://www.iastate.edu/',
  subaffiliationLink: 'https://www.imse.iastate.edu/',
  addressLink: 'https://maps.app.goo.gl/gMN2vPth4yKYm7pVA',
  googleScholar: 'https://scholar.google.com/citations?user=viHpZJQAAAAJ',
  github: 'https://github.com/danielye0010',
  linkedin: 'https://www.linkedin.com/in/danielye0001/',
  cloudflareAnalyticsToken: '5637619e1ab545d8b5be22e2111be3d8',
} as const;

export const absoluteUrl = (path: string) => `${site.url}${path}`;

// ---------- interface strings (src/data/i18n.yaml) ----------
const uiSchema = z.object({
  html_lang: z.string(),
  og_locale: z.string(),
  switch_label: z.string(),
  name: z.string(),
  alt_name: z.string(),
  position: z.string(),
  subaffiliation: z.string(),
  affiliation: z.string(),
  address: z.string(),
  avatar_alt: z.string(),
  image_alt: z.string(),
  links: z.object({ scholar: z.string(), github: z.string(), linkedin: z.string() }),
  lang_nav: z.string(),
  to_dark: z.string(),
  to_light: z.string(),
});
export const i18n = z.object({ en: uiSchema, 'zh-Hans': uiSchema }).parse(parse(i18nRaw));

// ---------- portfolio content (src/data/portfolio.json) ----------
const str = z.string();
const strs = z.array(z.string());
const portfolioSchema = z.looseObject({
  nav: z.array(str).length(5),
  research: str,
  research_intro: str,
  published: str,
  ongoing: str,
  paper_summary: str,
  paper: str,
  paper_link: str,
  code: str,
  metrology: str,
  projects: str,
  projects_intro: str,
  repo: str,
  upstream: str,
  themes: z.array(z.tuple([str, str])),
  processes: z.array(z.object({ id: str, name: str, title: str, text: str, image: str, alt: str, w: z.number(), h: z.number() })),
  software: z.array(
    z.object({
      name: str, kind: str, text: strs, url: str, image: str, image_alt: str, image_caption: str,
      link_label: str.optional(), tags: strs.optional(), upstream: str.optional(), upstream_label: str.optional(),
    }),
  ),
  equipment: z.array(z.object({ name: str, type: str, text: str, image: str, alt: str, model: str, subtitle: str })),
  am_heading: str,
  more_projects: str,
  engineering: str,
  engineering_intro: str,
  simulation_heading: str,
  simulation_intro: str,
  fabrication_heading: str,
  fabrication_intro: str,
  simulation: z.array(z.object({ id: str, name: str, title: str, skills: strs, tools: strs, image: str, alt: str })),
  creative_heading: str,
  creative_works: z.array(
    z.object({
      id: str, url: z.url(), name: str, original_title: str, kind: str, text: str, tags: strs,
      details_label: str.optional(), link_label: str, image: str, image_alt: str,
      image_width: z.number().optional(), image_height: z.number().optional(),
    }),
  ),
});
export type Portfolio = z.infer<typeof portfolioSchema>;
export const portfolio = z.object({ en: portfolioSchema, 'zh-Hans': portfolioSchema }).parse(portfolioJson);

// ---------- pages ----------
export type Kind = 'home' | 'research' | 'engineering' | 'projects' | 'creative';
export const kinds: Kind[] = ['home', 'research', 'engineering', 'projects', 'creative'];

export const prefix = (lang: Lang) => (lang === 'zh-Hans' ? '/zh/' : '/');
export const pathFor = (kind: Kind, lang: Lang) => (kind === 'home' ? prefix(lang) : `${prefix(lang)}${kind}/`);

/** Page titles, descriptions and keywords (formerly each page's front matter). */
export const pageMeta: Record<Kind, Record<Lang, { title: string; description?: string; keywords?: string }>> = {
  home: {
    en: {
      title: 'Daniel Ye | Ph.D. Candidate at Iowa State University',
      keywords: 'Daniel Ye, Industrial Engineering, Iowa State University, additive manufacturing, computational geometry, 3D deformation modeling, predictive compensation',
    },
    'zh-Hans': {
      title: '叶逸飞 Daniel Ye | 爱荷华州立大学博士候选人',
      description: '叶逸飞（Daniel Ye），爱荷华州立大学工业工程博士候选人，研究增材制造（3D 打印）中的三维变形建模与预测补偿，并关注三维深度学习、空间智能 与三维生成。',
      keywords: '叶逸飞, Yifei Ye, Daniel Ye, 爱荷华州立大学, Iowa State University, 工业工程, 增材制造, 3D 打印, 三维变形, 计算几何',
    },
  },
  research: { en: { title: 'Research | Daniel Ye' }, 'zh-Hans': { title: '研究 | Daniel Ye' } },
  engineering: { en: { title: 'Engineering | Daniel Ye' }, 'zh-Hans': { title: '工程 | Daniel Ye' } },
  projects: { en: { title: 'Projects | Daniel Ye' }, 'zh-Hans': { title: '项目 | Daniel Ye' } },
  creative: {
    en: {
      title: 'Creative | Daniel Ye',
      description: 'Fiction and film by Daniel Ye, including the short film The Unused Take and the short story collection No Sea in the Elevator.',
    },
    'zh-Hans': {
      title: '创作 | Daniel Ye',
      description: '叶逸飞 Daniel Ye 的文学与影像创作，包括 短片《备用影像》和短篇小说集《電梯裡沒有海》。',
    },
  },
};
