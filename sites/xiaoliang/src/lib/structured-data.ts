// schema.org JSON-LD for the profile page (ProfilePage + Person + ScholarlyArticle entries).
import { authorNames, homeUrl, profile, site, type Lang } from './profile';

export function structuredData(opts: { lang: Lang; url: string; pageTitle: string; description: string; htmlLang: string; avatarUrl: string; buildTime: Date }) {
  const p = profile;
  const person = `${homeUrl}#person`;
  const native = p.zh.name_native;

  const articles = [...p.research, ...p.other].map((pub) => {
    const author = authorNames(pub.authors).map((n) => (n === p.name ? { '@id': person } : { '@type': 'Person', name: n }));
    const base = {
      '@type': 'ScholarlyArticle',
      headline: pub.title,
      inLanguage: 'en',
      author,
      datePublished: 'year' in pub ? String(pub.year) : pub.venue.split(', ').at(-1),
      isPartOf: pub.venue.replaceAll('&#58;', ':'),
    };
    return 'links' in pub
      ? { ...base, url: pub.links[0]!.url, sameAs: pub.links.map((l) => l.url) }
      : { ...base, url: pub.url };
  });

  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'ProfilePage',
        '@id': `${opts.url}#profile-page`,
        url: opts.url,
        name: opts.pageTitle,
        description: opts.description,
        inLanguage: opts.htmlLang,
        dateModified: opts.buildTime.toISOString().replace(/\.\d{3}Z$/, '+00:00'),
        mainEntity: { '@id': person },
      },
      {
        '@type': 'Person',
        '@id': person,
        name: p.name,
        givenName: 'Xiao',
        familyName: 'Liang',
        ...(native ? { alternateName: [native, 'Liang Xiao'] } : {}),
        url: homeUrl,
        image: opts.avatarUrl,
        workLocation: { '@type': 'Place', name: 'Ames, Iowa', address: { '@type': 'PostalAddress', addressLocality: 'Ames', addressRegion: 'IA', addressCountry: 'US' } },
        logo: `${site}/assets/logo-512.png`,
        jobTitle: 'Ph.D. Student in Electrical and Computer Engineering',
        description: p.description.trim(),
        affiliation: {
          '@type': 'CollegeOrUniversity',
          name: 'Iowa State University',
          url: 'https://www.iastate.edu/',
          department: { '@type': 'Organization', name: 'Department of Electrical and Computer Engineering', url: 'https://www.ece.iastate.edu/' },
        },
        alumniOf: [
          { '@type': 'CollegeOrUniversity', name: 'Washington University in St. Louis', url: 'https://wustl.edu/' },
          { '@type': 'CollegeOrUniversity', name: 'North China University of Technology', url: 'https://www.ncut.edu.cn/' },
        ],
        knowsAbout: ['Nonconvex optimization', 'Optimization landscape analysis', 'Low-rank tensor recovery', 'Tensor sensing', 'Blind deconvolution', 'Phase retrieval', 'Signal processing'],
        sameAs: p.links.map((l) => l.url),
      },
      ...articles,
    ],
  };
}
