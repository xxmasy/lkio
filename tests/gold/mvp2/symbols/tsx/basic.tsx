/**
 * Gold Standard Fixture: TSX Basic Symbols
 */

import React from "react"

export function UserCard(props: { name: string }) {
  return (
    <div className="card">
      <h3>{props.name}</h3>
    </div>
  )
}

export const UserBadge = ({ status }: { status: string }) => {
  return <span className={status}>{status}</span>
}

export function useCardCounter(initialCount: number = 0) {
  return initialCount
}
