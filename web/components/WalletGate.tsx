"use client";

import { type ReactNode, useState } from "react";
import { useWallet } from "./WalletProvider";

export function WalletGate({ children }: { children: ReactNode }) {
  const { accountId, connecting, connect, ready } = useWallet();
  const [error, setError] = useState<string | null>(null);

  if (!ready) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--muted)",
        }}
      >
        Initializing wallet…
      </div>
    );
  }

  if (!accountId) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
        }}
      >
        <div
          style={{
            maxWidth: 420,
            width: "100%",
            textAlign: "center",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 16,
            padding: "2.5rem 2rem",
          }}
        >
          <h1 style={{ margin: "0 0 0.75rem", fontSize: "1.5rem" }}>On-Chain CPU</h1>
          <p style={{ margin: "0 0 1.5rem", color: "var(--muted)", lineHeight: 1.5 }}>
            Connect your HashPack wallet to train on-chain ML models on Hedera testnet.
            You will authorize a 200 HBAR spending allowance when you start training.
          </p>
          {error && (
            <p style={{ color: "var(--danger)", fontSize: "0.85rem", marginBottom: "1rem" }}>
              {error}
            </p>
          )}
          <button
            type="button"
            disabled={connecting}
            onClick={() => {
              setError(null);
              void connect().catch((e) =>
                setError(e instanceof Error ? e.message : String(e))
              );
            }}
            style={{
              width: "100%",
              background: "var(--accent)",
              border: "none",
              borderRadius: 10,
              padding: "0.85rem 1rem",
              fontSize: "1rem",
              fontWeight: 600,
              color: "#fff",
              cursor: connecting ? "wait" : "pointer",
            }}
          >
            {connecting ? "Connecting…" : "Connect Wallet"}
          </button>
          <p style={{ margin: "1.25rem 0 0", fontSize: "0.75rem", color: "var(--muted)" }}>
            Requires HashPack with WalletConnect enabled on Hedera testnet.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
