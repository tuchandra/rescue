# Pokemon Mystery Dungeon Rescue Team: DX Password Tool


## Development
This app uses [Tailwind CSS](https://tailwindcss.com/), which is a utility-based CSS framework that acts as a post-CSS processor. You'll notice in the [HTML](https://github.com/tuchandra/rescue/blob/master/index.html) that most elements have a lot of inline classes. These are Tailwind utility classes that style everything consistently without my having to write a ton of CSS.

Development requires Tailwind and assorted dependencies / sister packages. You can install them with `npm install` (I think; this is my first time developing with NPM). 

I use the `live-server` NPM package (installed globally) to live-preview the app as I'm developing, which has the nice feature of autoreloading files as they change. You don't have to do this; you could use `python -m http.server` if you wanted.

Usually, if you make changes to the HTML files, the page will automatically reload with the refreshed styles. If you make changes to Tailwind config or utilities (i.e., anything in [tailwind.config.js](https://github.com/tuchandra/rescue/blob/master/tailwind.config.js)), you'll need to rebuild the Tailwind CSS file using `npm run build`.

## Deployment
This is a static site deployed via Github Pages, hosted at [tusharc.dev/rescue](https://tusharc.dev/rescue) (where [tusharc.dev](https://tusharc.dev) is my normal Github Pages site hosted in the [tuchandra.github.io](https://github.com/tuchandra/tuchandra.github.io) repo). 

For deployment, we want to strip out the unnecessary Tailwind classes (see [docs](https://tailwindcss.com/docs/controlling-file-size)). We have to build the CSS *for production* using `npm run prod`, which uses (under the hood) PurgeCSS to get rid of unused classes.

