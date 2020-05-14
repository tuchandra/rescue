# Pokemon Mystery Dungeon Rescue Team: DX Password Tool


## Development
**tl;dr**: Clone the repo and run `npm install`. This should be enough, but this is my first time developing with NPM, so who knows. You'll also need to comment out the line `<base href="/rescue/">` in [index.html](https://github.com/tuchandra/rescue/blob/master/index.html).

**Details**: the main complexity in development comes from this app using [Tailwind CSS](https://tailwindcss.com/), which is a utility-based CSS framework that acts as a post-CSS processor. You'll notice in the [HTML](https://github.com/tuchandra/rescue/blob/master/index.html) that most elements have a lot of inline classes. These are Tailwind utility classes that style everything consistently without me having to write a ton of CSS.

In [index.html](https://github.com/tuchandra/rescue/blob/master/index.html), you'll need to comment out the line `<base href="/rescue/">`. This, I believe, is due to Github Pages: when deployed, everything is relative to [tusharc.dev/rescue](https://tusharc.dev/rescue), but locally, everything is just relative to the repo root. So, for instance, the relative links in [css/tailwind.css](https://github.com/tuchandra/rescue/blob/master/css/tailwind.css) will be broken if this isn't set correctly. (I'm still not totally sure if this is correct.)

Finally if you make changes to the HTML files, the page will automatically reload with the refreshed styles if you're using something like `live-server` (which I am). You don't have to do this; you can use `python -m http.server` if you want. Note that if you make changes to Tailwind config or utilities (i.e., anything in [tailwind.config.js](https://github.com/tuchandra/rescue/blob/master/tailwind.config.js)), you'll need to rebuild the generated Tailwind CSS file using `npm run build`.


## Deployment
This is a static site deployed via Github Pages, hosted at [tusharc.dev/rescue](https://tusharc.dev/rescue) (where [tusharc.dev](https://tusharc.dev) is my normal Github Pages site hosted in the [tuchandra.github.io](https://github.com/tuchandra/tuchandra.github.io) repo). 

For deployment, we want to strip out the unnecessary Tailwind classes (see [docs](https://tailwindcss.com/docs/controlling-file-size)). We have to build the CSS *for production* using `npm run prod`, which uses (under the hood) PurgeCSS to get rid of unused classes.

