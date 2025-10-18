# frozen_string_literal: true

Gem::Specification.new do |spec|
  spec.name          = "Heritage Road Map Foundation Blog"
  spec.version       = "0.1"
  spec.authors       = ["HRMF AI Assistant [Bot]"]
  spec.email         = ["mmehgoss@gmail.com"]

  spec.summary       = "Heritage Road Map Foundation - Botanical research on South African indigenous plants and medicinal plants" 
  spec.homepage      = "https://github.com/MrViincciLeRoy/startbootstrap-clean-blog-jekyll"
  spec.license       = "MIT"

  spec.files         = `git ls-files -z`.split("\x0").select { |f| f.match(%r{^(assets|_layouts|_includes|_sass|LICENSE|README)}i) }

  spec.add_runtime_dependency "jekyll", ">= 3.8.5"

  spec.add_development_dependency "bundler", "~> 2.0.1"
  spec.add_development_dependency "rake", "~> 12.0"
end
