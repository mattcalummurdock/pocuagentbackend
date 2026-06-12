import type { Metadata } from "next";
import "./globals.css";
import { WalletProvider } from "../components/WalletProvider";
import { WalletGate } from "../components/WalletGate";
import { ConnectWalletButton } from "../components/ConnectWalletButton";

export const metadata: Metadata = {
  title: "On-Chain CPU Training",
  description: "Hedera Agent Kit + Kaggle on-chain ML training",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <WalletProvider>
          <WalletGate>
            <header
              style={{
                borderBottom: "1px solid var(--border)",
                padding: "1rem 1.5rem",
                display: "flex",
                gap: "1.5rem",
                alignItems: "center",
                width: "100%",
              }}
            >
              <strong style={{ fontSize: "1.1rem" }}>On-Chain CPU</strong>
              <nav style={{ display: "flex", gap: "1rem" }}>
                <a href="/">Agent</a>
                <a href="/jobs">Jobs</a>
              </nav>
              <ConnectWalletButton />
            </header>
            <main className="app-main">{children}</main>
          </WalletGate>
        </WalletProvider>
      </body>
    </html>
  );
}
