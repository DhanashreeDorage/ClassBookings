import './globals.css';
import type { ReactNode } from 'react';
export const metadata={title:'Royaltica Morning Publishing Class',description:'Book a place in the Royaltica Publishing Morning Class'};
export default function RootLayout({children}:{children:ReactNode}){return <html lang="en"><body>{children}</body></html>}
