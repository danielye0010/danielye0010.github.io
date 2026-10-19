# Development-only compatibility for Jekyll 3.9's LogAdapter on Ruby 3.3.
# LogAdapter skips Logger#initialize; newer Logger#level expects this hash.
require 'logger'
module PortfolioLoggerCompatibility
  def level
    @level_override ||= {}
    super
  end
end
Logger.prepend(PortfolioLoggerCompatibility)
