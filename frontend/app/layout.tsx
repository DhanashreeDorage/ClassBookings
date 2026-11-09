import './globals.css';
import type { ReactNode } from 'react';
export const metadata={title:'Royaltica | The Morning Writers’ Salon',description:'Reserve your place in the Royaltica Publishing Morning Class — a daily hour devoted to the art and business of authorship.'};
export default function RootLayout({children}:{children:ReactNode}){return <html lang="en"><body>{children}</body></html>}
