/**
 * Gold Standard Fixture: JavaScript Basic Symbols
 */

export function calculateTotal(price, taxRate = 0.1) {
  return price * (1 + taxRate)
}

export class Logger {
  constructor() {
    this.prefix = "[APP]"
  }

  log(message) {
    console.log(this.prefix, message)
  }
}

export const formatCurrency = (amount) => {
  return "$" + amount.toFixed(2)
}

var globalCounter = 0
let sessionToken = null
export const TIMEOUT_MS = 5000
