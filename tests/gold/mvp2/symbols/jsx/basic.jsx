/**
 * Gold Standard Fixture: JSX Basic Symbols
 */

import React from "react"

export function SimpleBanner({ title }) {
  return <h1>{title}</h1>
}

export const ButtonGroup = ({ children }) => {
  return <div className="btn-group">{children}</div>
}

export function sanitizeInput(text) {
  return text.trim()
}
