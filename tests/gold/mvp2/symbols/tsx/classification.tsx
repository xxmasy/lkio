/**
 * Gold Standard Fixture: TSX Classification & Anti-False-Positive Rules
 */

import React from "react"

// Anti-false-positive 1: Returns JSX, but lowercase first letter -> NOT a Component!
export function createMarkup() {
  return <div>Markup text</div>
}

// Anti-false-positive 2: Starts with 'useful', not followed by uppercase/digit -> NOT a Hook!
export function usefulUtil(input: string) {
  return input.toUpperCase()
}

// Fragment component: uses JSX Fragment syntax
export const FragmentWrapper = () => (
  <>
    <div>Item 1</div>
    <div>Item 2</div>
  </>
)

// Hook arrow function
export const useToggle = (initial: boolean = false) => {
  return initial
}
