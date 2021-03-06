New on Version 0.4
===

## Parametric processes
... To describe a workflow according to a configuration file or a the content of a directory :
  * 'preprocesses' are run before the workflow is executed
  * you can add processes to a workflow with the new command ``tuttle-extend-workflow`` from a preprocesses
  * a new tutorial explains how it works in detail

## Other
  * coma is DEPRECATED to separate resources in dependency definitions. You should now use space instead
  * [docker images](https://hub.docker.com/r/tuttle/tuttle/) are available to use tuttle

## Bug fixes
  * escape process ids in the report
  * ``file://`` is not a valid resource
  * ``!shell`` does not stand for processor ``hell``


  
New on Version 0.3
===

## New "include" statement
... To split a tuttle project in several files

## More documentation
the reference lists all the resources and processors available

## New resources and processors :
  * PostgreSQL tables, views, functions and index resources
  * PostgreSQL Processor
  * https resources
  * AWS s3 resources (experimental)

## Better tests
Part of tuttle's job is to connect to third party tools. Integration tests must cover these tools, like Postgresql or a web server... Two methods have been developed :
  * mock the third party tool with some python code (web server, s3 server)
  * use the third party tool if it is installed on the machine (postgresql)

## A few bug fixes
  * bug on install that required jinja2 before installing dependencies

New on Version 0.2
===

## New resources and processors :
  * SQLite tables, views, triggers and index resources
  * SQLite Processor
  * http resources
  * download processor
  * Pyton Processor

## A few bug fixes

## And a tutorial as the first step to the doc !


V0.1 : first official release
===
The goal of 0.1 is to show the intended usage of tuttle, in term of command line workflow.