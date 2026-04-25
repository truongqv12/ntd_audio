import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { useHashRoute } from "./hooks/useHashRoute";
import { useStudioController } from "./hooks/useStudioController";
import { DashboardPage } from "./pages/DashboardPage";
import { CreateJobPage } from "./pages/CreateJobPage";
import { JobsPage } from "./pages/JobsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProvidersPage } from "./pages/ProvidersPage";
import { SettingsPage } from "./pages/SettingsPage";
import { VoicesPage } from "./pages/VoicesPage";
import { LibraryPage } from "./pages/LibraryPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { VoiceLabPage } from "./pages/VoiceLabPage";
import { MonitorPage } from "./pages/MonitorPage";
import { ScriptEditorPage } from "./pages/ScriptEditorPage";

function App() {
  const { route, setRoute } = useHashRoute();
  const controller = useStudioController();

  const page = (() => {
    switch (route) {
      case "dashboard":
        return (
          <DashboardPage
            metrics={controller.metrics}
            projects={controller.projects}
            liveEvents={controller.liveEvents}
            onOpenProjects={() => setRoute("projects")}
            onOpenNotifications={() => setRoute("notifications")}
          />
        );
      case "create":
        return (
          <CreateJobPage
            projects={controller.projects}
            selectedProject={controller.selectedProject}
            selectedProjectKey={controller.selectedProjectKey}
            onSelectProject={controller.setSelectedProjectKey}
            providers={controller.providers}
            voices={controller.voices}
            selectedVoice={controller.selectedVoice}
            onSelectVoice={controller.setSelectedVoice}
            sourceText={controller.sourceText}
            onSourceTextChange={controller.setSourceText}
            outputFormat={controller.outputFormat}
            onOutputFormatChange={controller.setOutputFormat}
            voiceParams={controller.voiceParams}
            voiceParameterSchemas={controller.voiceParameterSchemas}
            onVoiceParamChange={controller.updateVoiceParam}
            onCreateJob={async () => {
              const created = await controller.createSynthesisJob();
              if (created) setRoute("jobs");
            }}
            isSubmitting={controller.isSubmitting}
            errorMessage={controller.errorMessage}
          />
        );
      case "jobs":
        return <JobsPage jobs={controller.jobs} selectedJob={controller.selectedJob} onSelectJob={controller.setSelectedJob} />;
      case "script":
        return (
          <ScriptEditorPage
            projects={controller.projects}
            providers={controller.providers}
            voices={controller.voices}
            selectedProjectKey={controller.selectedProjectKey}
            onSelectProject={controller.setSelectedProjectKey}
            eventVersion={controller.liveEvents.length + controller.jobs.length}
            voiceParameterSchemas={controller.voiceParameterSchemas}
            mergeDefaults={controller.settingsOverview?.merge_defaults ?? {}}
          />
        );
      case "projects":
        return (
          <ProjectsPage
            projects={controller.projects}
            providers={controller.providers}
            selectedProjectKey={controller.selectedProjectKey}
            onSelectProject={controller.setSelectedProjectKey}
            onCreateProject={controller.createWorkspaceProject}
            onToggleArchive={controller.toggleArchiveProject}
          />
        );
      case "voices":
        return (
          <VoicesPage
            voices={controller.voices}
            providers={controller.providers}
            selectedVoice={controller.selectedVoice}
            onSelectVoice={controller.setSelectedVoice}
          />
        );
      case "library":
        return <LibraryPage jobs={controller.jobs} projects={controller.projects} />;
      case "notifications":
        return <NotificationsPage liveEvents={controller.liveEvents} onMarkSeen={controller.markNotificationsSeen} />;
      case "providers":
        return <ProvidersPage providers={controller.providers} />;
      case "monitor":
        return <MonitorPage />;
      case "voice-lab":
        return <VoiceLabPage providers={controller.providers} />;
      case "settings":
        return <SettingsPage health={controller.health} currentProject={controller.selectedProject} projects={controller.projects} providers={controller.providers} settingsOverview={controller.settingsOverview} onUpdateProject={controller.updateProjectDefaults} onRefresh={controller.refreshCatalog} />;
      default:
        return null;
    }
  })();

  return (
    <div className="dashboard-shell">
      <Sidebar
        route={route}
        onNavigate={setRoute}
        projectCount={controller.metrics.projectCount}
        healthyProviders={controller.metrics.healthyProviders}
        activeJobs={controller.metrics.activeJobs}
      />
      <div className="main-area">
        <Topbar
          route={route}
          currentProject={controller.selectedProject}
          unreadNotifications={controller.unreadNotifications}
          totalVoices={controller.metrics.voiceCount}
          onNavigate={setRoute}
        />
        {controller.errorMessage ? <div className="alert-banner">{controller.errorMessage}</div> : null}
        {page}
      </div>
    </div>
  );
}

export default App;
