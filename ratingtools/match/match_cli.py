
# external packages
from vs_library.cli import Node, NodeBundle, DecoyNode, textformat
from vs_library.cli.objects import Command, Display, Prompt, Table
from vs_library.vsdb import queries_cli
from vs_library.database import database_cli
from vs_library.tools import pandas_functions_cli


class ImportRatingWorksheet(pandas_functions_cli.ImportSpreadsheet):
    
    """Imports the ratings worksheet file"""
    
    def __init__(self, rating_worksheet, parent=None):

        """
        Parameters
        ----------
        rating_worksheet : match.RatingWorksheet
            Controller of this NodeBundle
        """
        
        name = 'import-rating-worksheet'
        self.rating_worksheet = rating_worksheet

        super().__init__(name, parent=parent)

    def _execute(self):
        return super()._execute(self.rating_worksheet.read)


class AnalyzeRatingWorksheet(NodeBundle):
    
    """Shows worksheet summary and allow user to retain or discard columns"""
    
    def __init__(self, rating_worksheet, parent=None):

        """
        Parameters
        ----------
        rating_worksheet : match.RatingWorksheet
            Controller of this NodeBundle
        """
        
        name = 'analyze-rating-worksheet'
        self.rating_worksheet = rating_worksheet

        # OBJECTS
        self.__table_0 = Table([[]], header=False, command=Command(self._execute))
        self.__prompt_0 = Prompt("There are columns that are not required for match, would you like to keep them?")
        self.__prompt_1 = Prompt("Select the columns you want to keep:", command=Command(self._keep_selected_columns))

        # NODES
        self.__entry_node = Node(self.__table_0, name=f'{name}_table-analysis', 
                             acknowledge=True, show_hideout=True)
        self.__node_0 = Node(self.__prompt_0, name=f'{name}_column-not-required', parent=self.__entry_node,
                             show_hideout=True, clear_screen=True)
        self.__node_1 = Node(self.__prompt_1, name=f'{name}_column-to-keep', parent=self.__node_0)
        self.__exit_node = DecoyNode(name=f'{name}_last-node', parent=self.__entry_node)

        self.__node_0.adopt(self.__exit_node)
        self.__node_1.adopt(self.__exit_node)

        # CONFIGURATIONS
        self.__table_0.table_header = "Worksheet Summary"
        self.__table_0.description = "Shows the summary of the worksheet imported."

        self.__prompt_0.options = {
            '1': Command(self.rating_worksheet.concat_not_required, value="Keep all columns",
                         command=Command(lambda: self.__node_0.set_next(self.__exit_node))),
            '2': Command(lambda: self.__node_0.set_next(self.__node_1), value="Keep selected Columns",
                         command=Command(self._populate_prompt)),
            '3': Command(lambda: self.__node_0.set_next(self.__exit_node), value="Discard all")
            }

        self.__prompt_1.multiple_selection = True

        super().__init__(self.__entry_node, self.__exit_node, name=name, parent=parent)
    
    def _execute(self):
        info = self.rating_worksheet.worksheet_info
        self.__table_0.table = [[textformat.apply('Number of Columns', emphases=['bold']), info['number_of_columns']],
                                [textformat.apply('Number of Rows', emphases=['bold']), info['number_of_rows']],
                                [textformat.apply('Columns Added', emphases=['bold']), info['columns_added']],
                                [textformat.apply('Columns not Required', emphases=['bold']), info['columns_not_required']]]

        if self.rating_worksheet.not_required_columns:
            self.__entry_node.set_next(self.__node_0)
        else:
            self.__entry_node.set_next(self.__exit_node)

    def _keep_selected_columns(self):
        selected_columns = [self.__prompt_1.options[o] for o in self.__prompt_1.responses]
        self.rating_worksheet.concat_not_required(selected_columns)
    
    def _populate_prompt(self):
        self.__prompt_1.options = {str(k): v for k, v in enumerate(self.rating_worksheet.not_required_columns, 1)}


class SelectQueryForms(NodeBundle):

    """Prompts user to select the appropriate query forms for candidate matching"""

    def __init__(self, query_tool, parent):
        
        """
        Parameters
        ----------
        query_tool : vs_library.database.QueryTool
            Controller of this NodeBundle
        """

        name = 'select-query'
        self.query_tool = query_tool
        
        # OBJECTS
        self.__prompt = Prompt("Are these rating for incumbents or for candidates?")
        
        # NODES
        self.__entry_node = Node(self.__prompt, name=f'{name}_choices', clear_screen=True, show_hideout=True)
        self.__exit_node = DecoyNode(name=f'{name}_last')

        self.__bundle_0 = queries_cli.IncumbentQueryForm(self.query_tool, parent=self.__entry_node)
        self.__bundle_1 = queries_cli.CandidateQueryForm(self.query_tool, parent=self.__entry_node)
        
        self.__bundle_0.adopt_node(self.__exit_node)
        self.__bundle_1.adopt_node(self.__exit_node)

        # CONFIGURATIONS
        self.__prompt.options = {
            '1': Command(lambda: self.__entry_node.set_next(self.__bundle_0.entry_node), value='Incumbents'),
            '2': Command(lambda: self.__entry_node.set_next(self.__bundle_1.entry_node), value='Candidates')
            }

        super().__init__(self.__entry_node, self.__exit_node, name=name, parent=parent)


class DatabaseConnection(NodeBundle):

    def __init__(self, connection_manager, connection_adapter, parent=None):
        
        name = 'rating-database-connection'

        # OBJECTS
        self.__display_0 = Display("Connection to the Vote Smart Database is required. Proceed to connection selection...")
        self.__prompt_0 = Prompt("{message}", command=Command(lambda: self._check_for_connection(connection_manager)))
        self.__prompt_1 = Prompt("Establish connection to \'{database}\' on \'{host}\'?",
                                 command=Command(self._format_message))

        # NODES
        self.__entry_node = Node(self.__display_0, name=f'{name}_connection-required', 
                             acknowledge=True, show_hideout=True, clear_screen=True)
        self.__node_0 = Node(self.__prompt_0, name=f'{name}_pick-new-or-existing', parent=self.__entry_node, 
                             show_hideout=True, clear_screen=True)
        self.__node_1 = Node(self.__prompt_1, name=f'{name}_to-connect-or-no',
                             show_hideout=True, clear_screen=True)

        self.__bundle_0 = database_cli.AddConnection(connection_manager, parent=self.__node_0)
        self.__bundle_1 = database_cli.SelectConnection(connection_manager, parent=self.__node_0)
        self.__bundle_2 = database_cli.EstablishConnection(connection_adapter, self.__bundle_1.selected_connection, 
                                                           selection_bundle=self.__bundle_1, parent=self.__node_1)
        self.__bundle_3 = database_cli.EditConnection(connection_manager, self.__bundle_1.selected_connection, parent=self.__node_1)

        self.__node_1.adopt(self.__node_0)
        self.__bundle_0.adopt_node(self.__node_0)
        self.__bundle_1.adopt_node(self.__node_1)
        self.__bundle_3.adopt_node(self.__node_0)

        # CONFIGURATIONS
        self.__bundle_0.entry_node.clear_screen = True
        self.__bundle_2.entry_node.clear_screen = True
        self.__bundle_3.entry_node.clear_screen = True

        self.__prompt_0.options = {
            '1': Command(lambda: self.__node_0.set_next(self.__bundle_0.entry_node), value="Create a New Connection"),
            '2': Command(lambda: self.__node_0.set_next(self.__bundle_1.entry_node), value="Use an Existing Connection")
            }

        self.__prompt_1.options = {
            '1': Command(lambda: self.__node_1.set_next(self.__bundle_2.entry_node), value="Yes, certainly"),
            '2': Command(lambda: self.__node_1.set_next(self.__bundle_3.entry_node), value="Edit Connection"),
            '3': Command(lambda: self.__node_1.set_next(self.__node_0), value="Return to Menu")
            }

        self.__prompt_0.exe_seq = 'before'
        self.__prompt_1.exe_seq = 'before'
        
        super().__init__(self.__entry_node, self.__bundle_2.exit_node, name=name, parent=parent)

    def _format_message(self):
        connection_info = next(iter(self.__bundle_1.selected_connection))
        self.__prompt_1.question.format_dict = {'host': connection_info.host,
                                            'database': connection_info.database}
    
    def _check_for_connection(self, connection_manager):
        connections, _ = connection_manager.read()

        if not connections:
            self.__prompt_0.question.format_dict = {'message': "There are no stored connections. Select the following:"}
            self.__prompt_0.options['2'].method = lambda: self.__node_0.engine_call('quit')
            self.__prompt_0.options['2'].value = "Exit Application"
        else:
            self.__prompt_0.question.format_dict = {'message': "Stored connections detected. Select the following:"}
            self.__prompt_0.options['2'].method = lambda: self.__node_0.set_next(self.__bundle_1.entry_node)
            self.__prompt_0.options['2'].value = "Use an Existing Connection"


class RatingMatch(NodeBundle):

    def __init__(self, query_tool, rating_worksheet, rating_harvest, query_form=None, parent=None):
        
        name = 'rating-match'
        self.query_tool = query_tool
        self.rating_worksheet = rating_worksheet
        self.rating_harvest = rating_harvest

        # OBJECTS
        self.__prompt_0 = Prompt("Things are set. Commence rating match?")
        self.__display_0 = Display("Begin match...", Command(self._execute))
        self.__table_0 = Table([], header=False)
        self.__display_1 = Display("Incomplete Matches detected. Query Results are required to be exported.")
        self.__prompt_1 = Prompt("Matches are free of errors. Do you want to export query results?")
        self.__prompt_2 = Prompt("Harvest file can be generated. Proceed?")
        
        # NODES
        self.__entry_node = Node(self.__prompt_0, name=f'{name}_commence',
                             show_hideout=True)
        self.__node_0 = Node(self.__display_0, name=f'{name}_execute', parent=self.__entry_node,
                             show_hideout=True, clear_screen=True, store=False)
        self.__node_1 = Node(self.__table_0, name=f'{name}_results', parent=self.__node_0, 
                             acknowledge=True)
        self.__node_2 = Node(self.__display_1, name=f'{name}_query-incomplete', 
                             acknowledge=True, clear_screen=True)
        self.__node_3 = Node(self.__prompt_1, name=f'{name}_query-complete')

        self.__exit_node = DecoyNode(name=f'{name}_last-node', parent=self.__node_3)
        
        self.__bundle_1 = ExportMatchedDf(None, parent=self.__node_1)
        self.__bundle_2 = database_cli.ExportQueryResults(self.query_tool, parent=self.__node_2)

        self.__node_3.adopt(self.__bundle_2.entry_node)

        self.__bundle_1.adopt_node(self.__node_2)
        self.__bundle_1.adopt_node(self.__node_3)
        self.__bundle_2.adopt_node(self.__exit_node)

        # CONFIGURATIONS
        self.__bundle_1.entry_node.clear_screen = True
        self.__bundle_2.entry_node.clear_screen = True

        self.__table_0.table_header = "Match Results"
        self.__table_0.description = "Above shows the results of the match"

        self.__prompt_0.options = {
            '1': Command(lambda: self.__entry_node.set_next(self.__node_0), value="Yes")
            }
        
        self.__prompt_1.options = {
            '1': Command(lambda: self.__node_3.set_next(self.__bundle_2.entry_node), value="Yes"),
            '2': Command(lambda: self.__node_3.set_next(self.__node_4), value="No")
            }

        self.__prompt_2.options = {
            '1': Command(lambda: self.__node_4.set_next(self.__bundle_3.entry_node), value="Yes"),
            '2': Command(lambda: self.__node_4.set_next(self.__exit_node), value="No")
            }

        if query_form:
            self.__entry_node.adopt(query_form.entry_node)
            self.__prompt_0.options['R'] = Command(lambda: self.__entry_node.set_next(query_form.entry_node), value="Return to Query Edit")

        super().__init__(self.__entry_node, self.__exit_node, name=name, parent=parent)

    def _execute(self):
        query_records = self.query_tool.results(as_format='records')

        df, match_info = self.rating_worksheet.match_records(query_records)

        self.__bundle_1.df = df

        self.__table_0.table = [['Match Score', f"{match_info['score']}%"],
                                ['Duplicate Rows', match_info['duplicates']],
                                ['Unmatched Rows', match_info['unmatched']],
                                ['Rows Need Review', match_info['review']]]

        if not(match_info['score'] == 100 and match_info['duplicates'] == 0 and match_info['review'] == 0):
            self.__bundle_1.set_next_node(self.__node_2)
        else:
            self.rating_harvest.df = df
            self.__bundle_1.set_next_node(self.__node_3)


class ExportMatchedDf(pandas_functions_cli.ExportSpreadsheet):

    def __init__(self, df, parent=None):

        name = 'export-matched-df'

        self.df = df
        super().__init__(name, parent)


    def _execute(self):
        return super()._execute(df=self.df)
