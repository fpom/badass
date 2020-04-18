# `badass`: (not so) bad assessments

`badass` helps to produce automated assessments of programming
projects. It is likely to produce bad assessments of good projects,
but good assessments of bad projects. Indeed, it can test:

 * if the project compiles
 * the return values of functions on defined test cases
 * static properties on the code
 * traces of the execution
 
But it cannot test:

 * code readability and clarity
 * algorithm relevance and quality
 * all the aspects one would like to test on good projects

So, bad projects are likely to fail on the first group of tests, while
good project will pass and thus remain to be assessed manually.

The main goal of `badass` is thus to quickly produce superficial
assessments for a large number of students, allowing to focus on the
best projects for a manual analysis.

## Security

`badass` will execute all foreign code inside a sandbox provided
by [`firejail`](http://firejail.wordpress.com/) so you won't harm your
system executing malicious or badly programmed projects.

## Current state and future

This is a very early version:

 * limited to C projects
 * tests are provided as the `main` function
 * other tests have to be programmed by hand to analyse:
   * the source code
   * the `strace` log of the program
 
In the future versions, we may have:

 * online submission of projects and report to the students on a given
   set of tests
 * final assessment on extended test
 * copy/paste detection between projects
 * a library of standard tests on source code and `strace` log

## Licence

`badass` (C) 2020, Franck Pommereau <franck.pommereau@univ-evry.fr>

> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
 
> This program is distributed in the hope that it will be useful, but
> WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
> General Public License for more details.
 
> You should have received a copy of the GNU General Public License
> along with this program. If not,
> see <https://www.gnu.org/licenses/>.
