"use client";

import { useWallet } from "./WalletProvider";

export function ConnectWalletButton() {
  const { accountId, connecting, connect, disconnect } = useWallet();

  if (accountId) {
    return (
      <button
        type="button"
        onClick={() => void disconnect()}
        style={{
          marginLeft: "auto",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "0.35rem 0.75rem",
          fontSize: "0.8rem",
          cursor: "pointer",
          color: "var(--text)",
        }}
      >
        {accountId} · Disconnect
      </button>
    );
  }

  return (
    <button
      type="button"
      disabled={connecting}
      onClick={() => void connect().catch(() => {})}
      style={{
        marginLeft: "auto",
        background: "var(--accent)",
        border: "none",
        borderRadius: 8,
        padding: "0.35rem 0.75rem",
        fontSize: "0.8rem",
        cursor: "pointer",
        color: "#fff",
      }}
    >
      {connecting ? "Connecting…" : "Connect HashPack"}
    </button>
  );
}
