// Loads src/data/profile.yaml and validates it at build time.
// A missing or misspelled field fails the build instead of rendering a blank spot on the page.
//
// Text fields may contain HTML entities and inline tags (e.g. "&ndash;", "<b>Xiao Liang</b>");
// pages render them as HTML, exactly as the original Jekyll site did.
import { z } from 'astro/zod';
import { parse } from 'yaml';
import raw from '../data/profile.yaml?raw';

const link = z.object({ label: z.string(), url: z.url() });
const profileLink = link.extend({ icon: z.string() });

const education = z.object({
  degree: z.string(),
  school: z.string(),
  years: z.string(),
  note: z.string(),
});

const research = z.object({
  id: z.string(),
  title: z.string(),
  authors: z.string(),
  venue: z.string(),
  badge: z.string(),
  year: z.number().int(),
  thumb: z.enum(['landscape', 'muon', 'tubal', 'sphere']),
  note: z.string(),
  tldr: z.string(),
  links: z.array(link).min(1),
  bibtex: z.string(),
});

const other = z.object({
  title: z.string(),
  authors: z.string(),
  venue: z.string(),
  url: z.url(),
});

const ui = z.object({
  html_lang: z.string(),
  og_locale: z.string(),
  switch_label: z.string(),
  page_title: z.string(),
  og_title_suffix: z.string(),
  portrait_alt: z.string(),
  email_label: z.string(),
  profiles_label: z.string(),
  theme_label: z.string(),
  lang_nav: z.string(),
  research: z.string(),
  other: z.string(),
  education: z.string(),
  copy: z.string(),
  copied: z.string(),
  copy_label: z.string(),
});

// Fields a language section may override; anything missing falls back to the English value.
const localized = z.object({
  url: z.url(),
  name_native: z.string().optional(),
  title: z.string().optional(),
  tagline: z.string().optional(),
  department: z.string().optional(),
  university: z.string().optional(),
  location: z.string().optional(),
  advisor: z.string().optional(),
  description: z.string().optional(),
  keywords: z.string().optional(),
  interests: z.array(z.string()).optional(),
  education: z.array(education).optional(),
});

const schema = z.object({
  name: z.string(),
  title: z.string(),
  tagline: z.string(),
  department: z.string(),
  department_link: z.url(),
  university: z.string(),
  university_link: z.url(),
  location: z.string(),
  email_user: z.string(),
  email_domain: z.string(),
  email_tld: z.string(),
  avatar: z.string().startsWith('/'),
  url: z.url(),
  advisor: z.string(),
  advisor_link: z.url(),
  links: z.array(profileLink),
  description: z.string(),
  keywords: z.string(),
  interests: z.array(z.string()),
  education: z.array(education),
  research: z.array(research),
  other: z.array(other),
  zh: localized,
  ui: z.object({ en: ui, 'zh-Hans': ui }),
});

export type Profile = z.infer<typeof schema>;
export type Lang = 'en' | 'zh-Hans';
export type Research = z.infer<typeof research>;

export const profile: Profile = schema.parse(parse(raw));

/** The two pages of the site, in language-switch order. */
export const pages: { lang: Lang; path: string }[] = [
  { lang: 'en', path: '/' },
  { lang: 'zh-Hans', path: '/zh/' },
];

export const site = 'https://xiaoliang.group';
export const homeUrl = `${site}/`;
export const homeUrlZh = `${site}/zh/`;
export const urlFor = (lang: Lang) => (lang === 'zh-Hans' ? homeUrlZh : homeUrl);

/** Per-language view of the profile, with English fallbacks (mirrors `L.x | default: p.x`). */
export function localize(lang: Lang) {
  const p = profile;
  const L = lang === 'zh-Hans' ? p.zh : {};
  const pick = <K extends keyof typeof p.zh & keyof Profile>(k: K) =>
    ((L as Partial<Profile>)[k] || p[k]) as Profile[K];
  const nativeName = p.zh.name_native ?? '';
  const heading = lang === 'zh-Hans' && nativeName ? nativeName : p.name;
  const ui = p.ui[lang];
  return {
    ui,
    heading,
    title: pick('title'),
    tagline: pick('tagline'),
    department: pick('department'),
    university: pick('university'),
    location: pick('location'),
    description: pick('description').trim(),
    keywords: pick('keywords').trim(),
    education: pick('education'),
    interests: pick('interests'),
    pageTitle: heading === p.name ? `${p.name} | ${ui.page_title}` : `${heading} ${p.name} | ${ui.page_title}`,
    url: urlFor(lang),
  };
}

/** Plain-text author names from an authors field like "<b>Xiao Liang</b><sup>*</sup>, Zhen Qin". */
export const authorNames = (authors: string) =>
  authors
    .replace(/<[^>]*>/g, '')
    .replaceAll('*', '')
    .replaceAll('&dagger;', '')
    .split(', ')
    .map((n) => n.trim());
