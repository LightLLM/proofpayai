import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'ProofPay AI | Industrial Purchasing Intelligence',description:'AI-assisted industrial procurement with human approvals and PayPal sandbox payment verification.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
