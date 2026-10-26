// schema.org JSON-LD: ProfilePage + Person on every page; Book and VideoObject on the Creative pages.
import type { Kind } from './site';

const person = {
  "@type": "Person",
  "@id": "https://danielye.net/#person",
  "name": "Daniel Ye",
  "alternateName": [
    "Yifei Ye",
    "叶逸飞",
    "Ye Yifei"
  ],
  "givenName": "Daniel",
  "familyName": "Ye",
  "url": "https://danielye.net/",
  "image": {
    "@type": "ImageObject",
    "url": "https://danielye.net/assets/img/danielavatar.jpg",
    "width": 800,
    "height": 800,
    "caption": "Daniel Ye"
  },
  "description": "Ph.D. candidate in Industrial Engineering at Iowa State University (Ames, Iowa), advised by Dr. Qing Li and a member of the Center for Nondestructive Evaluation. Research on modeling and correcting 3D shape deformation in additive manufacturing.",
  "jobTitle": "Ph.D. Candidate in Industrial Engineering",
  "affiliation": [
    {
      "@type": "CollegeOrUniversity",
      "@id": "https://www.iastate.edu/#org",
      "name": "Iowa State University",
      "url": "https://www.iastate.edu/",
      "department": {
        "@type": "Organization",
        "name": "Department of Industrial and Manufacturing Systems Engineering",
        "url": "https://www.imse.iastate.edu/"
      }
    },
    {
      "@type": "ResearchOrganization",
      "name": "Center for Nondestructive Evaluation",
      "url": "https://www.cnde.iastate.edu/",
      "parentOrganization": {
        "@id": "https://www.iastate.edu/#org"
      }
    }
  ],
  "workLocation": {
    "@type": "Place",
    "name": "Ames, Iowa",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "Ames",
      "addressRegion": "IA",
      "addressCountry": "US"
    }
  },
  "alumniOf": [
    {
      "@type": "CollegeOrUniversity",
      "name": "University of Wisconsin–Madison",
      "url": "https://www.wisc.edu/"
    },
    {
      "@type": "CollegeOrUniversity",
      "name": "University of Minnesota Duluth",
      "url": "https://www.d.umn.edu/"
    }
  ],
  "knowsAbout": [
    "Additive manufacturing",
    "3D shape deformation modeling",
    "Predictive geometric compensation",
    "Computational geometry",
    "Geometry processing",
    "3D deep learning",
    "Generative 3D"
  ],
  "sameAs": [
    "https://scholar.google.com/citations?user=viHpZJQAAAAJ",
    "https://github.com/danielye0010",
    "https://www.linkedin.com/in/danielye0001/"
  ]
} as const;

const creativeWorks = [
  {
    "@type": "Book",
    "@id": "https://danielye.net/creative/#no-sea-in-the-elevator",
    "name": "電梯裡沒有海",
    "alternateName": "No Sea in the Elevator",
    "bookFormat": "https://schema.org/EBook",
    "genre": "Short stories",
    "inLanguage": "zh-Hant",
    "author": {
      "@id": "https://danielye.net/#person"
    },
    "url": "https://www.amazon.com/dp/B0H14C6DS1",
    "mainEntityOfPage": "https://danielye.net/creative/"
  },
  {
    "@type": "VideoObject",
    "@id": "https://danielye.net/creative/#the-unused-take",
    "name": "The Unused Take",
    "alternateName": "备用影像",
    "description": "In 1969, a secret stand-in rehearses the Moon landing—ready to step into history if the live broadcast fails.",
    "genre": "Short film",
    "inLanguage": "zh-Hans",
    "uploadDate": "2026-10-22",
    "thumbnailUrl": "https://danielye.net/assets/img/creative/the-unused-take.jpg",
    "embedUrl": "https://www.youtube.com/embed/bbXrEGeO0bU",
    "url": "https://www.youtube.com/shorts/bbXrEGeO0bU",
    "creator": {
      "@id": "https://danielye.net/#person"
    },
    "mainEntityOfPage": "https://danielye.net/creative/"
  }
] as const;

export function structuredData(o: { url: string; title: string; description: string; htmlLang: string; kind: Kind; buildTime: Date }) {
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'ProfilePage',
        '@id': `${o.url}#profile-page`,
        url: o.url,
        name: o.title,
        description: o.description,
        inLanguage: o.htmlLang,
        dateModified: o.buildTime.toISOString().replace(/\.\d{3}Z$/, '+00:00'),
        mainEntity: { '@id': 'https://danielye.net/#person' },
      },
      person,
      ...(o.kind === 'creative' ? creativeWorks : []),
    ],
  };
}
