# genpod
GenPod - frontend app (low-code / no-code) for generating infra files and applications code-base

## Development guidelines:
**Should leverage storybookjs, dhiwise, devcontainer.json, codiumAI + codeiumAI to develop GenPod. There are no exceptions/excuses in this selection.**

**Should leverage [DeepSource](https://app.deepsource.com/login), [Guardrails](https://dashboard.guardrails.io/login), [Snyk](https://app.snyk.io/login) in your forked repo itself and resolve all security issues within your forked repo and then only submit PR to upstream main repo.** 

  > Use ReactFlow + Zustand for canvas & state management.

  > Use open API specifications for designing and developing any APIs - leverage [Insomnia](https://insomnia.rest/) tool for this.
  
  > **Test-Driven development approach is mandatory**.

  > Leverage tools like [cypress](https://www.cypress.io/), [miragejs](https://miragejs.com/), [microcks](https://microcks.io/) for functional testing (behavioral testing, api testing, E2E testing, etc.).

  > Items should be configurable from one place (folder/file(s)) for - colors, styles, images, icons, charts (apache echart, react d3js), etc. This means that the common items should be organized so that they can be used anywhere in the code, and if changed in the future they should be modified in one place, and that change should reflect in all places that are using those items.

  > Always check for the latest versions of dependency packages and update them - we already have scanning tools enabled on this repo. Look at the PRs & Security tab every week to check the security enhancement suggestions those tools provide and keep up with implementing them.

  > Unit tests & build should be automatic via CI pipeline.

  > Should show code coverage for testing via codecov.

  > Should follow openSSF standards and pass their suggestions. 
