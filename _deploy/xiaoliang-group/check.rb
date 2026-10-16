# Post-build checks for the standalone xiaoliang.group site. Exits non-zero on any problem.
#   ruby check.rb dist
require "pathname"

out = Pathname.new(ARGV.fetch(0)).expand_path
errors = []

%w[index.html zh/index.html 404.html llms.txt robots.txt sitemap.xml _redirects
   assets/xl.css assets/xl.js assets/avatar.jpg].each do |f|
  errors << "missing #{f}" unless (out + f).file?
end

text_files = Dir.glob(out.join("**/*.{html,txt,xml}").to_s)
text_files.each do |f|
  body = File.read(f, encoding: "UTF-8")
  rel = Pathname.new(f).relative_path_from(out)
  # Leftovers from the danielye.net/xiaoliang/ deployment.
  errors << "#{rel}: contains '/xiaoliang/'" if body.include?("/xiaoliang/")
  errors << "#{rel}: contains 'danielye.net'" if body.include?("danielye.net")
  next unless f.end_with?(".html")

  # Every root-relative href/src must resolve to a file in dist/.
  body.scan(/(?:href|src)="(\/[^"]*)"/).flatten.uniq.each do |link|
    next if link.start_with?("//")
    path = link.split(/[?#]/).first
    target = path.end_with?("/") ? out + path.delete_prefix("/") + "index.html" : out + path.delete_prefix("/")
    errors << "#{rel}: broken link #{link}" unless target.file?
  end
end

# Canonical URLs must point at the new domain.
{ "index.html" => "https://xiaoliang.group/", "zh/index.html" => "https://xiaoliang.group/zh/" }.each do |f, want|
  got = File.read(out + f, encoding: "UTF-8")[/<link rel="canonical" href="([^"]+)"/, 1]
  errors << "#{f}: canonical is #{got.inspect}, expected #{want}" unless got == want
end

if errors.empty?
  puts "check.rb: OK (#{text_files.size} text files checked)"
else
  warn errors.map { |e| "check.rb: #{e}" }
  exit 1
end
